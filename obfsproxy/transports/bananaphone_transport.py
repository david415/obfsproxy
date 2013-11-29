#!/usr/bin/env python

from obfsproxy.transports.base import BaseTransport
import obfsproxy.common.log as logging
from obfsproxy.network.buffer import Buffer

from bananaphone import rh_decoder, rh_encoder


log = logging.get_obfslogger()

class BananaphoneTransport(BaseTransport):
    
    def __init__(self, transport_config):
        pass

    def handle_socks_args(self, args):
        if not args:
            log.error("BananaphoneTransport: must specify server transport options")
            return

        for arg in args:
            key,value = arg.split('=')
            setattr(self, key, value)

        # BUG: modify bananaphone.py to
        # accept the abridged arg as boolean?
        if hasattr(self,'abridged'):
            self.abridged = '--abridged'
        else:
            # this is the only transport option which has a default value
            self.abridged = None

        if self.modelName == 'markov':
            args = [ self.corpus, self.order, self.abridged ]
        elif self.modelName == 'random':
            args = [ self.corpus ]
        else:
            log.error("BananaphoneTransport: unsupported model type")
            return

        self.encode = rh_encoder(self.encodingSpec, self.modelName, *args)
        self.decode = rh_decoder(self.encodingSpec)

    @classmethod
    def setup(cls, transport_config):

        # if we are the client then we receive the transport options
        # from handle_socks_args
        if cls.initiator:
            return

        transport_options = transport_config.getServerTransportOptions()
        if not transport_options:
            log.error("BananaphoneTransport: must specify server transport options")
            return

        for key in transport_options.keys():
            setattr(cls, key, transport_options[key])

       # BUG: modify bananaphone.py to
        # accept the abridged arg as boolean?
        if hasattr(cls,'abridged'):
            cls.abridged = '--abridged'
        else:
            # this is the only transport option which has a default value
            cls.abridged = None

        if cls.modelName == 'markov':
            args = [ cls.corpus, cls.order, cls.abridged ]
        elif cls.modelName == 'random':
            args = [ cls.corpus ]
        else:
            log.error("BananaphoneTransport: unsupported model type")
            return

        cls.encode = rh_encoder(cls.encodingSpec, cls.modelName, *args)
        cls.decode = rh_decoder(cls.encodingSpec)

    @classmethod
    def get_public_options(cls, transport_options):
        """ Only tell BridgeDB about our encodingSpec
        """
        return dict(encodingSpec = transport_options['encodingSpec'])

    def handshake(self, circuit):
        self.encoder = self.encode > circuit.downstream.write
        self.decoder = self.decode > circuit.upstream.write

    def receivedDownstream(self, data, circuit):
        self.decoder.send(data.read())
        return

    def receivedUpstream(self, data, circuit):
        self.encoder.send(data.read())
        return

    @classmethod
    def register_external_mode_cli(cls, subparser):
        subparser.add_argument('--corpus', type=str, help='Corpus file of words')
        subparser.add_argument('--encoding_spec', type=str, dest='encodingSpec', help='reverse hash encoding specification')
        subparser.add_argument('--model', type=str, dest='modelName')
        subparser.add_argument('--order', type=int)
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
    initiator = True
    pass

class BananaphoneServer(BananaphoneTransport):
    initiator = False
    pass

