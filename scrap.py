import json
import re
from typing import Dict, List
from pathlib import Path
from bs4 import BeautifulSoup
from utils import replaces


def deduplicate(data: List[Dict]):
    deduplicated = []
    ret = []
    for e in data:
        e_wo_source = {k: v for k, v in e.items() if k != 'source'}
        if e_wo_source not in deduplicated:
            deduplicated.append(e_wo_source)
            ret.append(e)
    return ret


def defualt_behavior(soup: BeautifulSoup):
    bodys = soup.select('.prob_maindiv')

    return [{
        "text": replaces(e.select_one('.pbody').select_one('.left_margin').text),
        "answer": replaces(e.select_one('.answer').text).replace('Ответ: ', ''),
    } for e in bodys]


def yesno_behavior(soup: BeautifulSoup):
    bodys = soup.select('.prob_maindiv')

    tasks = [e.select_one('.pbody') for e in bodys]
    answers = [e.select_one('.answer').text.replace('Ответ: ', '') for e in bodys]

    n_re = r'(\d+)\)'

    premises = []
    for t, a in zip(tasks, answers):
        for e in t.select('.left_margin'):
            if m := re.match(n_re, e.text):
                task_text = re.sub(n_re, '', e.text).strip()
                premises.append({
                    'statement': task_text,
                    'label': m.group(1) in a
                })
    
    return premises


def t_10_behavior(soup: BeautifulSoup):
    bodys = soup.select(".pbody")

    tasks = [replaces(e.text) for e in bodys[::2]]
    answers = [e.find_all('td')[-1].text for e in soup.select('.res_row')]

    return [{
        "text": t,
        "answer": a,
    } for t, a in zip(tasks, answers)]


def basis_behavior(soup: BeautifulSoup):
    bodys = soup.select('.prob_maindiv')

    s_re = r'\(\d+\)([^\(\n)]*)'
    n_re = r'^\d+\)([^\n]*)'
    sent_re = r'\(предложение \d\)'

    out = []
    for b in bodys:
        keys = b.select_one('.answer').text.replace('Ответ: ', '')
        keys = keys.split('|')[0]
        s = '\n'.join([e.text for e in b.select_one('.pbody').select('.left_margin')[2:]])
        sentences = re.findall(s_re, s)
        sentences = (replaces(t.strip()) for t in re.findall(s_re, s))
        if re.search(sent_re, s):
            answers = (replaces(re.sub(r'\(предложение \d\)', '', t)).strip() for t in re.findall(n_re, s, re.MULTILINE))
            # print(list(zip(sentences, answers)))
            # print(keys)

            out.extend([{
                'sentence': s,
                'basis': a,
                'label': str(i+1) in keys,
            } for i, (s, a) in enumerate(zip(sentences, answers))])
    
    return out


def phrase_conn_behavior(soup: BeautifulSoup):
    bodys = soup.select('.prob_maindiv')

    return [{
        "phrase": replaces(e.select_one('.pbody').select('b')[0].text.replace("«", "").replace("»", "")).strip(),
        "connection": replaces(e.select_one('.pbody').select('b')[1].text).strip(),
        "answer": replaces(re.sub(r'(?:ИЛИ|или|\|).*', '', re.search(r'Ответ\: ([^\xa0.]*)', e.select_one('.solution').text).group(1))).strip(),
    } for e in bodys if len(e.select_one('.pbody').select('b')) == 2]





FOLDERS = [
    {
        'name': 'math_tasks', 
        'behavior': defualt_behavior,
        'override_behavior': {
            '10th_task.html': t_10_behavior,
        },
        'postprocess': lambda x: [e for e in x if 'рисунк' not in e['text']],
    },
    {
        'name': 'yes_no_math_tasks', 
        'behavior': yesno_behavior,
    },
    {
        'name': 'russian_basis_tasks',
        'behavior': basis_behavior,
    },
    {
        'name': 'russian_phrase_conn_tasks',
        'behavior': phrase_conn_behavior,
    }
]

for folder_setup in FOLDERS:
    folder = Path(folder_setup['name'])
    folder_behavior = folder_setup.get('behavior', defualt_behavior)
    override_behavior = folder_setup.get('override_behavior', {})
    postprocess = folder_setup.get('postprocess', lambda x: x)

    folder_data = []

    for file in folder.glob('*.html'):
        print(f'Parsing {file.name}')
        behavior = override_behavior.get(file.name, folder_behavior)
        print(f'Using {behavior.__name__} behavior')
        with file.open(encoding='utf-8') as f:
            html = f.read()
        
        soup = BeautifulSoup(html, 'lxml')
        data = behavior(soup)
        data = postprocess(data)
        data = [{**e, 'source': file.name} for e in data]
        folder_data.extend(data)
    
    folder_data = deduplicate(folder_data)
    
    
    print(f'Writing {folder.name}.json')
    with open(f'{folder.name}.json', 'w', encoding='utf-8') as f:
        json.dump(folder_data, f, ensure_ascii=False, indent=2)