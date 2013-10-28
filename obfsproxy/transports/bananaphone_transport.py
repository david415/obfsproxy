#!/usr/bin/env python

from obfsproxy.transports.base import BaseTransport
import obfsproxy.common.log as logging
from obfsproxy.network.buffer import Buffer

from bananaphone import rh_decoder, rh_encoder
import hashlib


log = logging.get_obfslogger()

class BananaPhoneBuffer(object):

    def __init__(self, corpusFilename=None):
        self.output_bytes     = Buffer()
        self.output_words     = Buffer()
        self.encodingSpec     = 'words,sha1,4'
        self.modelName        = 'markov'
        self.corpusFilename   = corpusFilename

        self.encoder = rh_encoder(self.encodingSpec, self.modelName, self.corpusFilename) > self.wordSinkToBuffer
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

        transport_options = transport_config.getServerTransportOptions()
        if transport_options and 'corpus' in transport_options:
            log.debug("Setting corpus from server transport options: '%s'", transport_options['corpus'])
            self.corpus = transport_options['corpus']

        if not hasattr(self, 'corpus'):
            self.corpus = '/usr/share/dict/words'
            log.debug("Setting corpus to default: '%s'", self.corpus)

        self.bananaBuffer = BananaPhoneBuffer(corpusFilename=self.corpus)
        self.corpusHash = self.getCorpusHash()

    def getCorpusHash(self):
        BLOCKSIZE = 65536
        hasher = hashlib.sha1()
        fh  = open(self.corpus, 'rb')
        buf = fh.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = fh.read(BLOCKSIZE)
        hash = hasher.hexdigest()
        log.debug("local corpus hash %s", hash)
        return hash

    def handshake(self, circuit):
        if self.we_are_initiator:
            circuit.downstream.write(self.corpusHash)

    def receivedDownstream(self, data, circuit):
        if not self.we_are_initiator:
            if self.wait_for_hash:
                if len(data.peek()) != len(self.corpusHash):
                    return
                if data.peek() == self.corpusHash:
                    log.info("Handshake OK: client server corpus hash match!")
                    self.wait_for_hash = False
                    data.drain()
                    circuit.downstream.write('OK')
                    return
                else:
                    log.info("Handshake FAIL: client server corpus hash mismatch!")
                    data.drain()
                    circuit.downstream.write('FAIL')
                    return

            circuit.upstream.write(self.bananaBuffer.transcribeFrom(data.read()))
        else:
            if self.wait_for_reply:
                if data.peek() == 'OK':
                    log.info("Handshake OK: client server corpus hash match!")
                    self.wait_for_reply = False
                    data.drain()
                    return
                elif data.peek() == 'FAIL':
                    log.info("Handshake FAIL: client server corpus hash mismatch!")
                    data.drain()
                    circuit.downstream.close()
                    circuit.upstream.close()
                    return

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
    
    def __init__(self, transport_config):
        self.we_are_initiator = True
        self.wait_for_reply   = True

        BananaphoneTransport.__init__(self, transport_config)

class BananaphoneServer(BananaphoneTransport):
   
    def __init__(self, transport_config):
        self.we_are_initiator = False
        self.wait_for_hash    = True

        BananaphoneTransport.__init__(self, transport_config)


