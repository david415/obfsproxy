#!/usr/bin/env python

from obfsproxy.transports.base import BaseTransport
import obfsproxy.common.log as logging
from obfsproxy.network.buffer import Buffer

from bananaphone import rh_decoder, rh_encoder
from binascii import hexlify

# https://github.com/seanlynch/pynacl
import nacl

log = logging.get_obfslogger()


ST_WAIT_FOR_PUBLIC_KEY = 0
ST_WAIT_FOR_SECRET_KEY = 1
ST_ENCRYPTED           = 2


class BananaPhoneBuffer(object):

    def __init__(self, corpusFilename=None):
        self.output_bytes     = Buffer()
        self.output_words     = Buffer()
        self.encodingSpec     = 'words,sha1,4'
        self.modelName        = 'markov'
        self.corpusFilename   = corpusFilename

        self.pending_data_to_send = False

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

        self.remote_publicKey = None
        self.remote_secretkey = None
        self.secretKey = nacl.randombytes(nacl.crypto_stream_KEYBYTES)
        self.publicKey, self.privateKey = nacl.crypto_box_keypair()
        self.bananaBuffer = BananaPhoneBuffer(corpusFilename=self.corpus)

    def sendSecretKey(self, circuit):
        log.debug("sending secret key")
        nonce      = nacl.randombytes(nacl.crypto_box_NONCEBYTES)
        ciphertext = nacl.crypto_box(self.secretKey, nonce, self.publicKey, self.privateKey)

        log.debug(hexlify(ciphertext))
        circuit.upstream.write(ciphertext)

    def receivedSecretKey(self, data):
        log.debug("receivedSecretKey")
        log.debug("data len %s" % len(data))

        remote_secretKey = data.peek(nacl.crypto_stream_KEYBYTES)
        if len(remote_secretKey) == nacl.crypto_stream_KEYBYTES:
            log.debug("received secret key")
            log.debug(hexlify(remote_secretKey))
            self.remote_secretKey = remote_secretKey
            data.drain(nacl.crypto_stream_KEYBYTES)
            self.state = ST_ENCRYPTED
            return True
        log.debug("did NOT received secret key")
        log.debug("got:%s" % hexlify(remote_secretKey))
        return False        

    def receivedPublicKey(self, data):
        log.debug("receivedPublicKey data len %s" % len(data))
        if self.we_are_initiator:
            log.debug("client")
        else:
            log.debug("server")

        remote_publicKey = data.peek(nacl.crypto_box_PUBLICKEYBYTES)
        if len(remote_publicKey) == nacl.crypto_box_PUBLICKEYBYTES:
            log.debug("received public key")
            log.debug(hexlify(remote_publicKey))
            self.remote_publicKey = remote_publicKey
            data.drain(nacl.crypto_box_PUBLICKEYBYTES)
            return True
        log.debug("did NOT received public key")
        log.debug("got:%s" % hexlify(remote_publicKey))
        return False

    def handshake(self, circuit):
        if self.we_are_initiator:
            log.debug("initiating key exchange")
            log.debug("sending public key %s" % hexlify(self.publicKey))
            log.debug("client now awaiting server's public key")
            circuit.downstream.write(self.publicKey)
            self.state = ST_WAIT_FOR_PUBLIC_KEY

    def receivedDownstream(self, data, circuit):

        if self.state == ST_ENCRYPTED:

            if self.pending_data_to_send:
                log.debug("%s: We got pending data to send and our crypto is ready. Pushing!" % log_prefix)
                self.receivedUpstream(circuit.upstream.buffer, circuit)
                self.pending_data_to_send = False

            circuit.upstream.write(self.bananaBuffer.transcribeFrom(data.read()))
            return

        if self.we_are_initiator:

            if self.state == ST_WAIT_FOR_PUBLIC_KEY:
                if self.receivedPublicKey(data):
                    self.sendSecretKey(circuit)
                    log.debug("waiting for server's secret key")
                    self.state = ST_WAIT_FOR_SECRET_KEY
                return

            if self.state == ST_WAIT_FOR_SECRET_KEY:
                if self.receivedSecretKey(data):
                    log.info("key exchange complete!")
                    self.state = ST_ENCRYPTED
                return
        else:

            if self.state == ST_WAIT_FOR_PUBLIC_KEY:
                if self.receivedPublicKey(data):
                    log.debug("sending public key")
                    circuit.upstream.write(self.publicKey)
                    log.debug(hexlify(self.publicKey))
                    log.debug("waiting for client's secret key")
                    self.state = ST_WAIT_FOR_SECRET_KEY
                return

            if self.state == ST_WAIT_FOR_SECRET_KEY:
                if self.receivedSecretKey(data):
                    log.info("secret key received")
                    log.info("sending secret key")
                    self.sendSecretKey(circuit)
                    log.info("key exchange complete!")
                    self.self = ST_ENCRYPTED
                return

    def receivedUpstream(self, data, circuit):

        if self.state != ST_ENCRYPTED:
            log.debug("Got upstream data before key exchange. Caching. %s" % len(data))
            self.pending_data_to_send = True
            return

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

        BananaphoneTransport.__init__(self, transport_config)

class BananaphoneServer(BananaphoneTransport):
   
    def __init__(self, transport_config):
        self.we_are_initiator = False
        self.state            = ST_WAIT_FOR_PUBLIC_KEY

        BananaphoneTransport.__init__(self, transport_config)

