#!/usr/bin/env python
import webbrowser
import urllib
import urllib2
import re
from HTMLParser import HTMLParser
import argparse
from pprint import pprint
from StringIO import StringIO
import gzip

# create a subclass and override the handler methods
class MyHTMLParser(HTMLParser):
    title = ''
    q = ''
    state = 'looking'
    results = []

    def __init__(self, q):
        HTMLParser.__init__(self)
        self.q = q.lower()

    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.state = 'title'
        if tag == 'magnet' and self.state == 'matched':
            self.state = 'magnet'

    def handle_data(self, data):
        if self.state == 'title':
            if data.lower().find(self.q) != -1:
                self.title = data
                self.state = 'matched'
            else:
                self.state = 'looking'
        if self.state == 'magnet':
            self.results.append(['magnet:?xt=urn:btih:' + urllib.quote(data) + '&dn=' + urllib.quote(self.title), '?', '?'])
            self.state = 'looking'


def main():
    parser = argparse.ArgumentParser(description='Finds and downloads torrents from the Pirate Bay')
    parser.add_argument('q', metavar='search_term', help="The term to search for")
    parser.add_argument('--local', dest='database', help="An xml file containing the Pirate Bay database")
    parser.add_argument('-p', dest='pages', help="The number of pages to fetch (doesn't work with --local)", default=1)

    def local(args):
        xml_str = ''
        with open(args.database, 'r') as f:
            xml_str += f.read()
        htmlparser = MyHTMLParser(args.q)
        htmlparser.feed(xml_str)
        return htmlparser.results

    #todo: redo this with html parser instead of regex
    def remote(args):
        res_l = []
        try:
            pages = int(args.pages)
            if pages < 1:
                raise Exception('')
        except Exception:
            raise Exception("Please provide an integer greater than 0 for the number of pages to fetch.")

        # Catch the Ctrl-C exception and exit cleanly
        try:
            for page in xrange(pages):
                request = urllib2.Request('http://thepiratebay.se/search/' + args.q.replace(" ", "+") + '/' + str(page) + '/7/0')
                request.add_header('Accept-encoding', 'gzip')
                response = urllib2.urlopen(request)
                if response.info().get('Content-Encoding') == 'gzip':
                    buf = StringIO(response.read())
                    res = gzip.GzipFile(fileobj=buf).read()
                else:
                    res = response.read()
                # res = f.read(102400)
                found = re.findall(""""(magnet\:\?xt=[^"]*)|<td align="right">([^<]+)</td>""", res)

                # get sizes as well and substitute the &nbsp; character

                # print res
                # print f
                # print 'http://thepiratebay.se/search/' + args.q.replace(" ", "+") + '/' + str(page) + '0/99/0'

                sizes = [ match.replace("&nbsp;", " ") for match in re.findall("(?<=Size )[0-9.]+\&nbsp\;[KMGT]*[i ]*B",res) ]
                uploaded = [ match.replace("&nbsp;", " ") for match in re.findall("(?<=Uploaded ).+(?=\, Size)",res) ]
                # pprint(sizes); print len(sizes)
                # pprint(uploaded); print len(uploaded)
                state = "seeds"
                curr = ['',0,0] #magnet, seeds, leeches
                for f in found:
                    if f[1] == '':
                        curr[0] = f[0]
                    else:
                        if state == 'seeds':
                            curr[1] = f[1]
                            state = 'leeches'
                        else:
                            curr[2] = f[1]
                            state = 'seeds'
                            res_l.append(curr)
                            curr = ['', 0, 0]
        except KeyboardInterrupt :
            print "\nCancelled."
            exit()

        # return the sizes in a spearate list
        return res_l, sizes, uploaded

    args = parser.parse_args()
    if args.database:
        mags = local(args)
    else:
        mags, sizes, uploaded = remote(args)

    if mags and len(mags) > 0:
        # enhanced print output with column titles
        print "\n%-4s %-5s %-5s %-11s %-11s  %s" % ( "LINK", "SEED", "RATIO", "SIZE", "UPLOAD", "NAME")
        for m in range(len(mags)):
            magnet = mags[m]
            name = re.search("dn=([^\&]*)", magnet[0])

            # compute the S/L ratio (Higher is better)
            try:
                ratio = float(magnet[1])/float(magnet[2])
            except ZeroDivisionError:
                ratio = 0

            # enhanced print output with justified columns
            print "%-4s %-5s %5.1f %-11s %-11s  %s" % (m, magnet[1], ratio ,sizes[m], uploaded[m],urllib.unquote(name.group(1).encode('ascii')).decode('utf-8').replace("+", " ") )

        try:
            l_array = raw_input("Select links (separate with one space): ").split()
        except KeyboardInterrupt :
            print "\nCancelled."
            exit()

        for l in l_array :
            try:
                choice = int(l)
            except Exception:
                choice = None

            if not choice == None:
                webbrowser.open(mags[choice][0])
            else:
                print "Cancelled."
    else:
        print "no results"

if __name__ == "__main__":
    main()
