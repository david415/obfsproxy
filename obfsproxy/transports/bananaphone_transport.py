#!/usr/bin/env python

from obfsproxy.transports.base import BaseTransport
import obfsproxy.common.log as logging
from obfsproxy.network.buffer import Buffer

from bananaphone import rh_decoder, rh_encoder


log = logging.get_obfslogger()

class BananaPhoneBuffer(object):

    def __init__(self, corpusFilename=None, encodingSpec=None, modelName=None, order=None, abridged=None):
        self.corpusFilename   = corpusFilename
        self.encodingSpec     = encodingSpec
        self.modelName        = modelName
        self.order            = order
        self.abridged         = abridged

        self.output_bytes     = Buffer()
        self.output_words     = Buffer()

        # BUG: modify bananaphone.py to
        # accept the abridged arg as boolean?
        if self.abridged:
            self.abridged = '--abridged'
        else:
            self.abridged = None

        if self.modelName == 'markov':
            args = [ self.corpusFilename, self.order, self.abridged ]
        elif self.modelName == 'random':
            args = [ self.corpusFilename ]
        else:
            # Todo: print an error message?
            pass

        self.encoder = rh_encoder(self.encodingSpec, self.modelName, *args) > self.wordSinkToBuffer
        self.decoder = rh_decoder(self.encodingSpec) > self.byteSinkToBuffer


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

        self.bananaBuffer = BananaPhoneBuffer(corpusFilename = self.corpus,
                                              encodingSpec   = self.encodingSpec,
                                              modelName      = self.modelName,
                                              order          = self.order,
                                              abridged       = self.abridged)

    def receivedDownstream(self, data, circuit):
        circuit.upstream.write(self.bananaBuffer.transcribeFrom(data.read()))
        return

    def receivedUpstream(self, data, circuit):
        circuit.downstream.write(self.bananaBuffer.transcribeTo(data.read()))
        return

    @classmethod
    def register_external_mode_cli(cls, subparser):
        subparser.add_argument('--corpus', type=str, default='/usr/share/dict/words', help='Corpus file of words')
        subparser.add_argument('--encoding_spec', type=str, default='words,sha1,4', dest='encodingSpec', help='reverse hash encoding specification')
        subparser.add_argument('--model', type=str, default='markov', dest='modelName')
        subparser.add_argument('--order', type=int, default=1)
        subparser.add_argument('--abridged', action='store_true', default=False,)

        super(BananaphoneTransport, cls).register_external_mode_cli(subparser)

    @classmethod
    def validate_external_mode_cli(cls, args):
        cls.corpus       = args.corpus
        cls.encodingSpec = args.encodingSpec
        cls.modelName    = args.modelName
        cls.order        = args.order
        cls.abridged     = args.abridged
        super(BananaphoneTransport, cls).validate_external_mode_cli(args)


class BananaphoneClient(BananaphoneTransport):
    pass

class BananaphoneServer(BananaphoneTransport):
    pass

