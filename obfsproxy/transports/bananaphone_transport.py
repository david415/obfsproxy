#!/usr/bin/env python

from obfsproxy.transports.base import BaseTransport
import obfsproxy.common.log as logging
from obfsproxy.network.buffer import Buffer

from bananaphone import rh_decoder, rh_encoder, parseEncodingSpec, buildWeightedRandomModel, truncateHash, readTextFile, markov


log = logging.get_obfslogger()

class BananaPhoneBuffer(object):

    def __init__(self, corpusFilename=None, encodingSpec=None, modelName=None, order=None, abridged=None):

        log.debug("BananaPhoneBuffer: __init__")

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

        self.tokenize, self.hash, self.bits = parseEncodingSpec(self.encodingSpec)

        log.debug("BananaPhoneBuffer: creating %s model" % self.modelName)

        if self.modelName == 'markov':
            args = { 'corpusFilename': self.corpusFilename,
                     'order': self.order,
                     'abridged': self.abridged }

            self.model = markov ( self.tokenize,
                                  self.hash,
                                  self.bits,
                                  corpusFilename = self.corpusFilename,
                                  order = self.order,
                                  abridged = self.abridged )

        elif self.modelName == 'random':
            args = { 'corpusFilename': self.corpusFilename }
            self.corpusTokens   = list( self.tokenize < readTextFile( self.corpusFilename ) )
            self.truncatedHash  = truncateHash(self.hash, self.bits)
            self.model = buildWeightedRandomModel(self.corpusTokens, self.truncatedHash)
        else:
            log.info("BananaPhoneBuffer: invalid model")
            return None

        self.encoder = rh_encoder(encodingSpec=self.encodingSpec, model=self.model, **args) > self.wordSinkToBuffer
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
        pass

    def receivedDownstream(self, data, circuit):
        circuit.upstream.write(self.bananaBuffer.transcribeFrom(data.read()))
        return

    def receivedUpstream(self, data, circuit):
        circuit.downstream.write(self.bananaBuffer.transcribeTo(data.read()))
        return

    @classmethod
    def setup(cls):
        print "my setup!"
        print cls.__dict__.keys()

        cls.bananaBuffer = BananaPhoneBuffer(corpusFilename = cls.corpus,
                                             encodingSpec   = cls.encodingSpec,
                                             modelName      = cls.modelName,
                                             order          = cls.order,
                                             abridged       = cls.abridged)

    @classmethod
    def register_external_mode_cli(cls, subparser):

        log.debug("register_external_mode_cli")

        subparser.add_argument('--corpus', type=str, default='/usr/share/dict/words', help='Corpus file of words')
        subparser.add_argument('--encoding_spec', type=str, default='words,sha1,4', dest='encodingSpec', help='reverse hash encoding specification')
        subparser.add_argument('--model', type=str, default='markov', dest='modelName')
        subparser.add_argument('--order', type=int, default=1)
        subparser.add_argument('--abridged', action='store_true', default=False,)

        super(BananaphoneTransport, cls).register_external_mode_cli(subparser)

    @classmethod
    def validate_external_mode_cli(cls, args):

        log.debug("validate_external_mode_cli")

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

