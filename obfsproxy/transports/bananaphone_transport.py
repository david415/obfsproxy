#!/usr/bin/env python

from obfsproxy.transports.base import BaseTransport
import obfsproxy.common.log as logging
from obfsproxy.network.buffer import Buffer


import nacl
from bananaphone import hammertime_rh_server


log = logging.get_obfslogger()

class BananaPhoneBuffer(object):

    def __init__(self, corpusFilename=None):
        self.output_bytes     = Buffer()
        self.output_words     = Buffer()
        self.encodingSpec     = 'words,sha1,4'
        self.modelName        = 'markov'
        self.corpusFilename   = corpusFilename

        self.key = nacl.randombytes(nacl.crypto_stream_KEYBYTES)

        (self.encoder, self.decoder) = hammertime_rh_server(key          = self.key,
                                                            encodingSpec = self.encodingSpec, 
                                                            model        = self.modelName,
                                                            filename     = self.corpusFilename)

        self.encoder = self.encoder > self.wordSinkToBuffer
        self.decoder = self.decoder > self.byteSinkToBuffer


    def transcribeFrom(self, input):
        for byte in input:
            self.decoder.send(byte)
        return self.output_bytes.read()

    def transcribeTo(self, input):
        for byte in input:
            self.encoder.send(byte)
        return self.output_words.read()

    def wordSinkToBuffer(self, input):
        self.output_words.write(input)

    def byteSinkToBuffer(self, input):
        self.output_bytes.write(input)
 

class BananaphoneTransport(BaseTransport):
    
    def __init__(self, transport_config):

        transport_options = transport_config.getServerTransportOptions()
        if transport_options and 'corpus' in transport_options:
            log.debug("Setting corpus from server transport options: '%s'", transport_options['corpus'])
            self.corpus = transport_options['corpus']

        if not hasattr(self, 'corpus'):
            self.corpus = '/usr/share/dict/words'
            log.debug("Setting corpus to default: '%s'", self.corpus)

        self.bananaBuffer = BananaPhoneBuffer(corpusFilename=self.corpus)

    def receivedDownstream(self, data, circuit):
        circuit.upstream.write(self.bananaBuffer.transcribeFrom(data.read()))
        return

    def receivedUpstream(self, data, circuit):
        circuit.downstream.write(self.bananaBuffer.transcribeTo(data.read()))
        return

    @classmethod
    def register_external_mode_cli(cls, subparser):
        subparser.add_argument('--corpus', type=str, help='Corpus file of words')
        super(BananaphoneTransport, cls).register_external_mode_cli(subparser)

    @classmethod
    def validate_external_mode_cli(cls, args):
        if args.corpus:
            cls.corpus = args.corpus
        super(BananaphoneTransport, cls).validate_external_mode_cli(args)


class BananaphoneClient(BananaphoneTransport):
    pass

class BananaphoneServer(BananaphoneTransport):
    pass

