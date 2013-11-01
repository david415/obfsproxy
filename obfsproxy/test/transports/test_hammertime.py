#!/usr/bin/env python

from obfsproxy.network.buffer import Buffer
from cocotools import cdebug, pv
from bananaphone import hammertime_client
from scapy.all import hexdump


class Test_Hammertime(object):

    def __init__(self):
        (self.encoder, self.decoder) = hammertime_client()

        self.output_bytes = Buffer()
        self.output_words = Buffer()
        self.encoder = self.encoder > self.wordSinkToBuffer
        self.decoder = self.decoder > self.byteSinkToBuffer

    def transcribeTo(self, input):
        for byte in input:
            self.encoder.send(byte)
        return self.output_words.read()

    def byteSinkToBuffer(self, input):
        self.output_bytes.write(input)

    def wordSinkToBuffer(self, input):
        self.output_words.write(input)

def main():

    test = Test_Hammertime()
    test.transcribeTo('hello')
    buff = test.output_words.read()

    print "buff len == %s" % len(buff)
    

    

if __name__ == '__main__':
    main()
