#!/usr/bin/env python

"""Usage: python file_receiver.py

Demonstrates a server that receives a multipart-form-encoded set of files in an
HTTP POST, or streams in the raw data of a single file in an HTTP PUT.

See file_uploader.py in this directory for code that uploads files in this format.
"""

import logging

try:
    from urllib.parse import unquote
except ImportError:
    # Python 2.
    from urllib import unquote

import tornado.ioloop
import tornado.web
from tornado import options
import tempfile
import os

MB = 1024 * 1024
GB = 1024 * MB
TB = 1024 * GB

MAX_STREAMED_SIZE = 30*MB

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        #self.write('<form action="/upload" method="post" enctype="multipart/form-data"><input type="file" name="file" id="file" /><br /><input type="submit" value="upload" /></form>')
        self.render("upload.html")

@tornado.web.stream_request_body
class POSTHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.bytes_read = 0
        self.meta = dict()
        self.receiver = self.get_receiver()

    def prepare(self):
        """If no stream_request_body"""
        self.request.connection.set_max_body_size(MAX_STREAMED_SIZE)

    def data_received(self, chunk):
        self.receiver(chunk)

    def get_receiver(self):
        index = 0
        SEPARATE = b'\r\n'

        def receiver(chunk):
            nonlocal index
            if index == 0:
                index +=1
                split_chunk             = chunk.split(SEPARATE)
                self.meta['boundary']   = SEPARATE + split_chunk[0] + b'--' + SEPARATE
                self.meta['header']     = SEPARATE.join(split_chunk[0:3])
                self.meta['header']     += SEPARATE *2
                self.meta['filename']   = split_chunk[1].split(b'=')[-1].replace(b'"',b'').decode()

                chunk = chunk[len(self.meta['header']):]
                import os
                self.fp = open(os.path.join('upload',self.meta['filename']), "wb")
                self.fp.write(chunk)
            else:
                self.fp.write(chunk)
        return receiver

    def post(self, *args, **kwargs):        
        self.meta['content_length'] = int(self.request.headers.get('Content-Length')) - \
                                      len(self.meta['header']) - \
                                      len(self.meta['boundary'])

        self.fp.seek(self.meta['content_length'], 0)
        self.fp.truncate()
        self.fp.close()
        self.finish('OK')
           

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/upload", POSTHandler),
        
    ])


if __name__ == "__main__":
    # Tornado configures logging.
    options.parse_command_line()
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()

