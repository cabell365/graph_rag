import argparse
import json
import re
from pathlib import Path
from .graph import Graph
from .retrieval import retrieve, answer_stream

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit',type=int,default=0)
    parser.add_argument('--ids',default='',help='Comma-separated question IDs for focused checks')
    parser.add_argument('--output',default='reports/evaluation-results.jsonl')
    args = parser.parse_args()
    graph = Graph()
    questions = [json.loads(line) for line in (graph.s.data/'corpus/evaluation.jsonl').read_text().splitlines()]
    if args.ids:
        questions = [q for q in questions if q['question_id'] in args.ids.split(',')]
    if args.limit:
        questions = questions[:args.limit]
    output = Path(args.output)
    output.parent.mkdir(exist_ok=True)
    try:
        with output.open('w') as report:
            for item in questions:
                evidence = retrieve(graph,item['question'])
                answer = ''.join(answer_stream(graph,item['question'],evidence))
                retrieved = sorted(set(s['id'] for s in evidence.sources))
                cited = sorted(set(re.findall(r'\[(DOC-[A-Z0-9-]+|SOURCE-[a-f0-9]+|FINANCE)\]',answer)))
                expected = item.get('supporting_documents',[])
                result = {**item,'answer':answer,'retrieved':retrieved,'cited':cited,
                    'expected_source_recall':len(set(expected)&set(retrieved))/len(expected) if expected else None,
                    'unsupported_citations': sorted(set(cited)-set(retrieved)-({'FINANCE'} if evidence.finance and evidence.finance.get('available') else set())),
                    'human_review_required':True}
                report.write(json.dumps(result)+'\n')
                report.flush()
                print(item['question_id'],result['expected_source_recall'],flush=True)
    finally:
        graph.close()

if __name__=='__main__':
    main()
