#!/usr/bin/env python

from obfsproxy.transports.base import BaseTransport
import obfsproxy.common.log as logging
from obfsproxy.network.buffer import Buffer

from bananaphone import rh_decoder, rh_encoder


log = logging.get_obfslogger()

class BananaphoneTransport(BaseTransport):
    
    def __init__(self, transport_config):
        pass

    @classmethod
    def setup(cls, transport_config):
        
        transport_options = transport_config.getServerTransportOptions()
        if transport_options:
            for key in transport_options.keys():
                setattr(cls, key, transport_options[key])

        # default transport options
        if not hasattr(cls, 'corpus'):
            cls.corpus       = '/usr/share/dict/words'
        if not hasattr(cls, 'encodingSpec'):
            cls.encodingSpec = 'words,sha1,4'
        if not hasattr(cls, 'modelName'):
            cls.modelName    = 'markov'
        if not hasattr(cls, 'order'):
            cls.order        = 1
        if not hasattr(cls, 'abridged'):
            cls.abridged     = False

        # BUG: modify bananaphone.py to
        # accept the abridged arg as boolean?
        if cls.abridged:
            cls.abridged = '--abridged'
        else:
            cls.abridged = None

        if cls.modelName == 'markov':
            args = [ cls.corpus, cls.order, cls.abridged ]
        elif cls.modelName == 'random':
            args = [ cls.corpus ]
        else:
            log.error("BananaPhoneBuffer: unsupported model type")
            return

        cls.encode = rh_encoder(cls.encodingSpec, cls.modelName, *args)
        cls.decode = rh_decoder(cls.encodingSpec)

    @classmethod
    def get_public_options(cls, transport_options):
        # make encodingSpec transport option public
        # if not specified then use the default value
        if 'encodingSpec' not in transport_options:
            return dict(encodingSpec = cls.encodingSpec)
        else:
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

