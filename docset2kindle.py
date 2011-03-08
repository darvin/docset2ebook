#! /usr/bin/env python

import json
import codecs
import re
from os import path, system, makedirs, remove, walk
from shutil import copyfile, copytree, rmtree, move

def main():
    #docset_path = '/Library/Developer/Documentation/DocSets/com.apple.adc.documentation.AppleiOS4_2.iOSLibrary.docset'
    docset_path = '/Developer/Documentation/DocSets/com.apple.adc.documentation.AppleSnowLeopard.CoreReference.docset'
    
    print "Scanning docset for books..."
    valid_book_types = set(['Guide', 'Getting Started'])
    book_paths_by_title = books(docset_path, valid_book_types)
    print len(book_paths_by_title), ' books found. Starting conversion...'
    
    f = open('kindle.css', 'r')
    stylesheet = f.read()
    f.close()
    
    for book_path in book_paths_by_title.values():
        build_mobi(book_path, stylesheet)


def books(docset_path, valid_book_types):
    doc_paths = list()
    for paths in walk(docset_path):
        filenames = paths[2]
        if 'book.json' in filenames:
            doc_paths.append(paths[0])
    doc_path_dict = dict()
    for doc_path in doc_paths:
        book_path = path.join(doc_path, 'book.json')
        f = open(book_path, 'r')
        book = json.loads(f.read())
        book_type = get_book_type(book)
        book_title = book.get('title')
        f.close()
        if len(valid_book_types) == 0 or book_type in valid_book_types:
            doc_path_dict[book_title] = doc_path
    return doc_path_dict


def get_book_type(book):
    book_assignments = book.get('assignments')
    book_type = None
    if book_assignments:
        for assignment in book_assignments:
            if assignment.startswith('Type/'):
                book_type = assignment[len('Type/'):]
    return book_type


def build_mobi(doc_path, stylesheet):
    book_path = path.join(doc_path, 'book.json')
    f = open(book_path, 'r')
    book = json.loads(f.read())
    book_title = book.get('title')
    print '  ' + book_title
    f.close()
    
    documents = document_paths(book)
    
    work_dir = 'temp'
    if path.isdir(work_dir): rmtree(work_dir)
    copytree(doc_path, work_dir)
    
    absolute_paths = [path.join(work_dir, doc_path) for doc_path in documents]
    
    for absolute_path in absolute_paths:
        try:
            f = codecs.open(absolute_path, 'r', 'utf-8')
            doc = f.read()
            f.close()
            cleaned_doc = clean_doc(doc, stylesheet)
            f = codecs.open(absolute_path, 'w', 'utf-8')
            f.write(cleaned_doc)
            f.close()
        except IOError, error:
            print error
            continue
    
    html_toc = gen_html_toc(book)
    toc_path = path.join(work_dir, 'toc.html')
    f = codecs.open(toc_path, 'w', 'utf-8')
    f.write(html_toc)
    f.close()
    
    ncx = gen_ncx(book)
    ncx_path = path.join(work_dir, 'toc.ncx')
    f = codecs.open(ncx_path, 'w', 'utf-8')
    f.write(ncx)
    f.close()
    
    opf = gen_opf(book)
    opf_path = path.join(work_dir, 'kindle.opf')
    f = codecs.open(opf_path, 'w', 'utf_8')
    f.write(opf)
    f.close()
    
    kindlegen_cmd = './kindlegen' + ' temp/kindle.opf -o output.mobi > /dev/null'
    system(kindlegen_cmd)
    
    if not path.isdir('output'): makedirs('output')
    
    filename = book_title.replace('/', '_') + '.mobi'
    dest_path = path.join('output', filename)
    try:
        move('temp/output.mobi', dest_path)
        rmtree('temp')
    except IOError, error:
        print error


def gen_opf(book):
    title = book.get('title')
    
    opf = '''<?xml version="1.0" encoding="utf-8"?>
        <package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="BookId">
        <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">'''
    opf += '<dc:title>' + title + '</dc:title>'
    opf += '<dc:language>en-us</dc:language>'
    opf += '<meta name="cover" content="My_Cover" />'
    opf += '<dc:creator>Apple Inc.</dc:creator>'
    opf += '<dc:publisher>Apple Inc.</dc:publisher>'
    opf += '<dc:subject>Reference</dc:subject>'
    opf += '</metadata>'
    
    opf += '<manifest>'
    opf += '<item id="My_Cover" media-type="image/gif" href="../cover.gif" />'
    opf += '<item id="toc" media-type="application/xhtml+xml" href="toc.html" />'
    i = 1
    all_docs = document_paths(book)
    for doc in all_docs:
        opf += '<item id="chapter_' + str(i) + '" media-type="application/xhtml+xml" href="' + doc + '" />'
        i += 1
    opf += '<item id="My_Table_of_Contents" media-type="application/x-dtbncx+xml" href="toc.ncx"></item>'
    
    opf += '</manifest>'
    
    opf += '<spine toc="My_Table_of_Contents">'
    opf += '<itemref idref="toc"/>'
    i = 1
    for doc in all_docs:
        opf += '<itemref idref="chapter_' + str(i) + '"/>'
        i += 1
    opf += '</spine>'
    
    opf += '<guide>'
    opf += '<reference type="toc" title="Table of Contents" href="toc.html"/>'
    opf += '<reference type="text" title="Text" href="' + list(all_docs)[0] + '" />'
    opf += '</guide>'
    opf += '</package>'
    return opf
    
    
def gen_ncx(book):
    header = '''<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN"
    	"http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
        <ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="en-US">
        <head>
        <meta name="dtb:uid" content="BookId"/>
        <meta name="dtb:depth" content="1"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
        </head>'''
    footer = '</ncx>' 
    navmap = '<navMap>' + gen_nav_map(book) + '</navMap>'
    ncx = header + navmap + footer
    return ncx

def gen_nav_map(book):
    sections = book.get('sections')
    navmap = ''
    navmap += '<navPoint class="chapter" id="chapter_0" playOrder="0"><navLabel><text>Table of Contents</text></navLabel><content src="toc.html"/></navPoint>'
    order = 1
    for section in sections:
        navmap += '<navPoint class="chapter" id="chapter_' + str(order) + '" playOrder="' + str(order) + '">'
        title = section.get('title')
        navmap += '<navLabel><text>' + title + '</text></navLabel>'
        href = section.get('href')
        navmap += '<content src="' + href + '"/>'
        navmap += '</navPoint>'
        order += 1
    return navmap

def gen_html_toc(book):
    toc = html_toc_fragment(book)
    book_title = book.get('title')
    header = '''<html><head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <title>Table of Contents</title>
        <body><h1>''' + book_title + '</h1><h2 style="margin-top: 1em;">Table of Contents</h2>'
    footer = '</body></html>'
    return header + toc + footer


def html_toc_fragment(book):
    sections = book['sections']
    toc = '<ul>'
    for section in sections:
        href = section.get('href')
        title = section.get('title')
        toc += '<li><a href="' + href + '">' + title + '</a></li>'
        if section.get('sections'):
            toc += html_toc_fragment(section)
    toc += '</ul>'
    return toc


def clean_doc(doc, stylesheet):
    head_pattern = re.compile(r'(<meta id=.*)</head>', re.DOTALL)
    cleaned_doc = re.sub(head_pattern, '<style>' + stylesheet + '</style></head>', doc)
    feedback_pattern = re.compile(r'<div id="feedbackForm.*</div>', re.DOTALL)
    cleaned_doc = re.sub(feedback_pattern, '', cleaned_doc)
    tail_scripts_pattern = re.compile(r'</body>(.*)</html>', re.DOTALL)
    cleaned_doc = re.sub(tail_scripts_pattern, '</html>', cleaned_doc)
    cleaned_doc = re.sub('</?article.*>', '', cleaned_doc)
    navigation_links_pattern = re.compile(r'<div id="pageNavigationLinks.*?</div>', re.DOTALL)
    cleaned_doc = re.sub(navigation_links_pattern, '', cleaned_doc)
    copyright_footer_pattern = re.compile(r'<div class="copyright".*</div>', re.DOTALL)
    cleaned_doc = re.sub(copyright_footer_pattern, '', cleaned_doc)
    return cleaned_doc
    
    
def document_paths(book):
    sections = book.get('sections')
    if sections is None: return []
    docs_set = set()
    docs_list = list()
    for section in sections:
        href = section.get('href')
        if href:
            path = href.split('#', 1)[0]
            if path not in docs_set:
                docs_set.add(path)
                docs_list.append(path)
        subsections = section.get('sections')
        if subsections:
            subsection_docs = document_paths(section)
            for path in subsection_docs:
                if path not in docs_set:
                    docs_set.add(path)
                    docs_list.append(path)
    return docs_list
    
    
if __name__ == '__main__':
    main()
    