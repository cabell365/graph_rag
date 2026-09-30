import datetime
import html
import json
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from graphrag.graph import Graph
from graphrag.llm import Ollama
from graphrag.retrieval import retrieve, answer_stream, finance_query

st.set_page_config(page_title='Canyon • Knowledge Commons', page_icon='🌲', layout='wide')
st.markdown('''<style>
.stApp {background:radial-gradient(ellipse at top right,#193a28 0%,#0b1410 50%)}
h1,h2,h3{font-family:Georgia,serif!important} .block-container{max-width:1350px;padding-top:2.4rem}
.eyebrow{color:#b5c9a4;letter-spacing:.24em;font-size:.7rem;font-weight:700}
.hero{border-bottom:1px solid #365240;padding:0 0 26px;margin-bottom:24px}
.hero h1{font-size:3rem;letter-spacing:-.04em;margin:8px 0}.hero p{color:#b9c7b9;max-width:700px}
[data-testid=stChatMessage]{background:#14251bcc;border:1px solid #2c4233;border-radius:16px}
div.stButton>button{border-radius:10px;border-color:#426348}
</style>''',unsafe_allow_html=True)

@st.cache_resource
def connection():
    return Graph()

def evidence_view(payload):
    sources = payload.get('sources', [])
    with st.expander(f'Evidence desk · {len(sources)} passages', expanded=False):
        for source in sources:
            st.markdown(f'**[{source["id"]}] {source["title"]}**')
            st.caption(f'{source["origin"]} · {source.get("valid_from") or "undated"} → {source.get("valid_to") or "unspecified"} · {source["path"]}')
            st.text(source['text'])
    if payload.get('edges'):
        with st.expander('Relationship map & provenance'):
            edges = payload['edges'][:25]
            # Native Graphviz renderer; all labels are escaped, no external JS.
            dot = ['digraph G { graph [bgcolor="#14251B",rankdir=LR]; node [shape=box,style="rounded,filled",fillcolor="#275D38",fontcolor="#EDF3E9",color="#72936b"]; edge [color="#95b488",fontcolor="#d8dfd4"];']
            for e in edges:
                dot.append(f'{json.dumps(e["source"])} -> {json.dumps(e["target"])} [label={json.dumps(e["relationship"])}];')
            st.graphviz_chart('\n'.join(dot)+'}')
            st.dataframe(edges, use_container_width=True)
    if payload.get('finance'):
        with st.expander('Finance query provenance'):
            st.json(payload['finance'])

with st.sidebar:
    st.markdown('### 🌲 Canyon Commons')
    st.caption('LOCAL KNOWLEDGE • CONNECTED EVIDENCE')
    page = st.radio('Workspace', ['Chat', 'Finance explorer', 'Library', 'Learning room'])
    use_date = st.toggle('Use an event date', value=False)
    date = st.date_input('Event date', value=datetime.date(2023,1,1), disabled=not use_date)
    as_of = date.isoformat() if use_date else None
    st.caption('Scenario policies cover 2018–2024. A date helps select the right historical version.')
    if st.button('New conversation', use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    try:
        graph = connection()
        stats = graph.stats()
        st.success('Neo4j connected')
        st.caption(f'{stats["documents"]} documents · {stats["chunks"]} passages · {stats["metrics"]:,} finance records')
        models = Ollama(graph.s).health()
        missing = {graph.s.chat_model,graph.s.embed_model} - set(models)
        if missing:
            st.warning('Missing Ollama models: '+', '.join(sorted(missing)))
        else:
            st.success('Ollama models ready')
    except Exception as error:
        st.error('Services need attention')
        st.caption(str(error))
        graph,stats = None,{}
    st.divider()
    st.caption('mistral:latest · nomic-embed-text:latest')
    st.caption('Fictional business corpus. Financial figures originate in the supplied backup.')

st.markdown('<div class="hero"><div class="eyebrow">CANYON OFFICE / KNOWLEDGE COMMONS</div><h1>Ask. Connect. Understand.</h1><p>Explore policies, accounts and performance through connected knowledge. Every answer begins with evidence.</p></div>',unsafe_allow_html=True)

if page == 'Learning room':
    topic = st.selectbox('Read', ['Neo4j 101','System design'])
    file = Path('docs/neo4j-101.html' if topic=='Neo4j 101' else 'docs/design.html')
    if file.exists():
        st.download_button('Download HTML guide', file.read_bytes(), file.name, 'text/html')
        components.html(file.read_text(), height=900, scrolling=True)
    st.stop()

if not graph:
    st.info('Follow README.md to start Neo4j and Ollama, then import the sources. The Learning room is available while services are offline.')
    st.stop()

if page == 'Finance explorer':
    st.subheader('Performance, with a paper trail')
    st.caption('Exact totals from the full backup. Team membership reflects the dump, not a historical roster.')
    with st.form('finance'):
        c1,c2,c3 = st.columns(3)
        year = c1.selectbox('Year',range(2018,2025),index=5)
        month = c2.selectbox('Month',['Full year']+list(range(1,13)))
        scope = c3.selectbox('Scope',['Network','Sales representative','Sales team'])
        idvalue = st.number_input('Rep ID or team ID (ignored for Network)', min_value=1, value=100001, step=1)
        run = st.form_submit_button('Calculate from source records')
    if run:
        try:
            result = finance_query(graph,year,None if month=='Full year' else month,
                idvalue if scope=='Sales representative' else None,idvalue if scope=='Sales team' else None)
            if not result['available']:
                st.warning(result.get('reason','No matching records. Check the ID and filters.'))
            else:
                a,b,c = st.columns(3)
                a.metric('Actual sales',f'${result["actual"]:,.2f}')
                b.metric('Target sales',f'${result["target"]:,.2f}')
                c.metric('Attainment',f'{result["attainment_percent"]}%')
                st.caption(f'{result["rows"]:,} source rows · [FINANCE] finance_backup.sql')
            st.json(result)
        except Exception as error:
            st.error(str(error))
    st.stop()

if page == 'Library':
    st.subheader('The source collection')
    rows = graph.query('MATCH (d:Document) RETURN d.id AS id,d.title AS title,d.origin AS origin,d.effective_from AS valid_from,d.effective_to AS valid_to,d.path AS path ORDER BY d.id')
    st.dataframe(rows,use_container_width=True,hide_index=True)
    choice = st.selectbox('Read source',[r['id'] for r in rows]) if rows else None
    if choice:
        texts = graph.query('MATCH (c:Chunk)-[:PART_OF]->(d:Document {id:$id}) RETURN c.text AS text ORDER BY c.id',id=choice)
        for row in texts:
            st.text(row['text'])
    st.stop()

if 'messages' not in st.session_state:
    st.session_state.messages = []
if not st.session_state.messages:
    cols = st.columns(3)
    starters = ['Who manages Aspen Grove and which team is involved?',
                'What pricing applies to Aspen Grove A4 paper in 2023?',
                'What were actual and target sales for REP-100001 in January 2018?']
    for col,q in zip(cols,starters):
        if col.button(q,use_container_width=True):
            st.session_state.pending = q
for item in st.session_state.messages:
    with st.chat_message(item['role'],avatar='🌲' if item['role']=='assistant' else '👤'):
        st.markdown(item['content'])
        if item.get('evidence'):
            evidence_view(item['evidence'])
prompt = st.chat_input('Ask about an account, policy, product or sales result…')
prompt = prompt or st.session_state.pop('pending',None)
if prompt:
    with st.chat_message('user',avatar='👤'):
        st.markdown(prompt)
    history = [{'role':m['role'],'content':m['content']} for m in st.session_state.messages]
    st.session_state.messages.append({'role':'user','content':prompt})
    with st.chat_message('assistant',avatar='🌲'):
        try:
            with st.spinner('Finding passages and tracing relationships…'):
                evidence = retrieve(graph,prompt,as_of)
            if not evidence.sources and not evidence.finance:
                text = 'No supporting evidence was found for that question and date. Try another date or a specific entity ID.'
                st.markdown(text)
            else:
                text = st.write_stream(answer_stream(graph,prompt,evidence,history,as_of))
            payload = {'sources':evidence.sources,'edges':evidence.edges,'finance':evidence.finance}
            evidence_view(payload)
            st.session_state.messages.append({'role':'assistant','content':text,'evidence':payload})
        except Exception as error:
            st.error(f'Could not complete this answer: {error}')
            st.caption('Check service status and ingestion, then retry your question.')
if st.session_state.messages:
    st.download_button('Export conversation and evidence',json.dumps(st.session_state.messages,indent=2,default=str),
                       'canyon-conversation.json','application/json')
