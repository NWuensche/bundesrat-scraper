#!/usr/bin/env python
# coding: utf-8

# In[1]:


import json
import itertools
import os
import re
from urllib.parse import urlsplit

import requests
from lxml import html as etree

import pdfcutter


# In[2]:


BASE_URL = 'https://www.landesvertretung.bremen.de'
INDEX_URL = 'https://www.diebevollmaechtigte.bremen.de/service/bundesratsbeschluesse-17466'
PDF_URL = 'https://www.diebevollmaechtigte.bremen.de/sixcms/media.php/13/{number}.%20BR-Sitzung_Kurzbericht.pdf'


# In[3]:


LINK_TEXT_RE = re.compile(r'(\d+)\. Sitzung')

def get_pdf_urls():
    response = requests.get(INDEX_URL)
    root = etree.fromstring(response.content)
    names = root.xpath('.//ul/li/a/span')
    for name in names:
        text = name.text_content()
        num = LINK_TEXT_RE.search(text)
        if num is None:
            continue
        num = int(num.group(1))
        yield num, PDF_URL.format(number=num)


# In[4]:


PDF_URLS = dict(get_pdf_urls())
PDF_URLS={935: PDF_URLS[935], 962: PDF_URLS[962]}


# In[5]:


os.makedirs('./_cache', exist_ok=True)

def get_filename_url(url):
    splitresult = urlsplit(url)
    filename = splitresult.path.replace('/', '_')
    filename = os.path.join('./_cache', filename)
    if os.path.exists(filename):
        return filename
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception('{} not found'.format(url))
    with open(filename, 'wb') as f:
        f.write(response.content)
    return filename

def get_session_pdf_filename(session):
    url = PDF_URLS[session['number']]
    return get_filename_url(url)


# In[6]:


with open('../bundesrat/sessions.json') as f:
    sessions = json.load(f)
len(sessions)


# In[7]:


def with_next(iterable):
    a, b = itertools.tee(iterable)
    next(b, None)
    return itertools.zip_longest(a, b)


# In[8]:

def reformat_top_num2(top_num):
    try:
        num = int(top_num)
        return str(num) + "."
    except ValueError: # Wenn z.B. 48 a hinter Nummer
        # TODO Hier noch mit a, b,... umgehen
        test = '{} {}'.format(top_num[:-1]+ ".", top_num[-1] + ")") # TODO Ändern
        #print("TEST")
        #print(test)
        #test = '{}'.format(top_num[:-1]) # TODO Ändern
        #return test + "."
        return test

def reformat_top_num(top_num):
    try:
        num = int(top_num)
        return top_num.zfill(3)
    except ValueError: # Wenn z.B. 48 a hinter Nummer
        test = '{} {}'.format(top_num[:-1].zfill(3), top_num[-1])
        return test

def get_reformatted_tops(top_nums):
    return [reformat_top_num(t) for t in top_nums]

def get_reformatted_tops2(top_nums):
    #TODO Wieder in List
    #return [reformat_top_num2(t) for t in top_nums]

    l=[reformat_top_num2(t) for t in top_nums]
    #https://stackoverflow.com/questions/480214/how-do-you-remove-duplicates-from-a-list-whilst-preserving-order
    seen = set()
    seen_add = seen.add
    return [x for x in l if not (x in seen or seen_add(x))]


def get_beschluesse_text(session, filename):
    cutter = pdfcutter.PDFCutter(filename=filename)
    debugger = cutter.get_debugger()
    #print("cutter")
    #print(cutter.filter(page=1).clean_text())

    session_number = session['number']

    print(session_number)
    if (session_number == 935):
        top_nums = [t['number'] for t in session['tops'] if t['top_type'] == 'normal']
        reformatted_top_nums = get_reformatted_tops2(top_nums)
        page_heading = cutter.filter(search='Beschlüsse der {}. Sitzung des Bundesrates'.format(session_number))[0] #Nur bei 935
        page_number = list(cutter.filter(search='1', page=1))[-1]
    else:
        top_nums = [t['number'] for t in session['tops'] if t['top_type'] == 'normal']
        reformatted_top_nums = get_reformatted_tops(top_nums)
        page_heading = cutter.filter(search='Ergebnisse der {}. Sitzung des Bundesrates'.format(session_number))[0] #Nur bei 962
        page_number = list(cutter.filter(search='1', page=1))[-1]
    #print("top_nums")
    #print(top_nums)
    #print("reformatted_top_nums")
    #print(reformatted_top_nums)

    #TODO Hier weiter - Bei 935 statt 001 ist 1. geschrieben

    column_two = 705

    #e.g. 1, (001, 002)
    for top_num, (current, next_) in zip(top_nums, with_next(reformatted_top_nums)):
        print("top_num") #e.g. 2
        print(top_num)
        print("current") #e.g. 002, 2.
        print(current)
        print("next_") #e.g. 003, 3.
        print(next_)
        if('.' in current):#935
            if('a)' in current):
                current_top = cutter.filter(auto_regex='^{}\.$'.format(current.split()[0][:-1])) #Could be 46. or 46. a)-> Just want 46
            elif(')' in current): #935 - 46. b) -> No 46. in Page anymore
                current_top = cutter.filter(auto_regex='^{}'.format(current.split()[-1].replace(')', '\\)')))
                curr_num = current.split()[0]
                current_num = cutter.filter(auto_regex='^{}$'.format(curr_num))
                current_top = current_top.below(current_num)[0]
            else:
                current_top = cutter.filter(auto_regex='^{}\.$'.format(current[:-1])) #Could be 46. or 46. a)-> Just want 46
        else:
            current_top = cutter.filter(auto_regex='^{}$'.format(current))

        print("current_top")
        print(current_top.clean_text())

        next_top = None
        if next_ is not None:
            if('.' in next_):#935
                if('a)' in next_): #935 - 46. a)
                    next_top = cutter.filter(auto_regex='^{}\.$'.format(next_.split()[0][:-1]))
                elif(')' in next_): #935 - 46. b)
                    next_top = cutter.filter(auto_regex='^{}'.format(next_.split()[-1].replace(')', '\\)')))
                    next_num = next_.split()[0]
                    next_top = next_top.below(current_top)[0]
                else:
                    next_top = cutter.filter(auto_regex='^{}\.$'.format(next_[:-1]))
            else:
                next_top = cutter.filter(auto_regex='^{}$'.format(next_))
        if(next_top is not None):
            print("next_top")
            print(next_top.clean_text())

        senats = cutter.filter(auto_regex='^Senats-?') | cutter.filter(auto_regex='^Beschluss$')
        senats = senats.below(current_top)
        if next_top:
            senats = senats.above(next_top)

        ergebnis_br = cutter.filter(auto_regex='^Ergebnis BR$').below(current_top)
        print("ergebnis_br")
        print(ergebnis_br)
        if next_top:
            ergebnis_br = ergebnis_br.above(next_top)
            
        senats_text = cutter.all().filter(
            doc_top__gte=senats.doc_top -1 ,
            top__gte=page_heading.bottom,
            bottom__lt=page_number.bottom,
            right__lt=column_two #TODO Bei 935 nicht vorhanden
        )
        print("SENAT:")
        print(senats_text.right_of(senats).clean_text())

        br_text_next_to = cutter.all().filter(
            doc_top__gte=ergebnis_br.doc_top,#Relativ zu allenSeiten
            top__gte=page_heading.bottom, #Relativ zu allen
            bottom__lt=page_number.bottom,
            right__lt=column_two #TODO Bei 935 nicht vorhanden
        )
        br_text_under = cutter.all().filter(
            doc_top__gte=ergebnis_br.doc_top -1 ,#Relativ zu allenSeiten
            top__gte=page_heading.bottom, #Relativ zu allen
            bottom__lt=page_number.bottom,
            right__lt=column_two #TODO Bei 935 nicht vorhanden
        )
        #TODO NEXT 935 - TOP a), b)
        #TODO NEXT 973 Entscheidungen -> Beschlüsse
#TODO Rein        br_text = br_text_next_to | br_text_under
        br_text = br_text_under
        print("br_text 2 before")
        print(br_text)
        print("br_text_next_to")
        print(br_text_next_to)
        print("br_text_under")
        print(br_text_under)

        if next_top:
            br_text = br_text.above(next_top)
            senats_text = senats_text.above(ergebnis_br)

        print("br_text before")
        print(br_text)

        senats_text = senats_text.right_of(senats)
        br_text = br_text.right_of(ergebnis_br)

        print("br_text")
        print(br_text)

        yield top_num, {'senat': senats_text.clean_text(), 'bundesrat': br_text.clean_text()}


# In[9]:


def get_session(session):
    try:
        filename = get_session_pdf_filename(session)
    except KeyError:
        return
    return dict(get_beschluesse_text(session, filename))


# In[10]:


FILENAME = 'session_tops.json'
if os.path.exists(FILENAME):
    with open(FILENAME) as f:
        session_tops = json.load(f)
else:
    session_tops = {}

for session in sessions:
    num = session['number']
#    print('Session', num)
    if str(num) in session_tops:
        continue
    result = get_session(session)
    if result is None:
        continue
    session_tops[str(num)] = result
    with open(FILENAME, 'w') as f:
        json.dump(session_tops, f)

print('Total sessions:', len(session_tops))


# In[ ]:




