#!/usr/bin/env python

from obfsproxy.transports.base import BaseTransport
import obfsproxy.common.log as logging

from bananaphone import rh_encoder, rh_decoder


log = logging.get_obfslogger()

class BananaPhoneBuffer(object):

    def __init__(self):
        self.output     = []

        encoder             = rh_encoder("words,sha1,13", "markov", "/usr/share/dict/words")
        self.encoder_target = encoder > self.byteSinkToBuffer
        self.decoder_target = rh_decoder("words,sha1,13") > self.byteSinkToBuffer

    def transcribeFrom(self, input):
        for byte in input:
            self.decoder_target.send(byte)
        self.decoder_target.close()
        return "".join(self.output)

    def transcribeTo(self, input):
        for byte in input:
            self.encoder_target.send(byte)
        self.encoder_target.close()
        return "".join(self.output)

    def drain(self):
        self.output = []

    def byteSinkToBuffer(self, input):
        self.output.append(input)


class BananaphoneTransport(BaseTransport):
    
    def __init__(self, transport_config):
        self.bananaBuffer = BananaPhoneBuffer()

    def receivedDownstream(self, data, circuit):
        circuit.upstream.write(self.bananaBuffer.transcribeTo(data.read()))

    def receivedUpstream(self, data, circuit):
        circuit.downstream.write(self.bananaBuffer.transcribeFrom(data.read()))


class BananaphoneClient(BananaphoneTransport):
    pass

class BananaphoneServer(BananaphoneTransport):
    pass

