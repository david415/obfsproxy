#!/usr/bin/env python

from obfsproxy.transports.base import BaseTransport
import obfsproxy.common.log as logging
from obfsproxy.network.buffer import Buffer

from bananaphone import rh_build_encoder_factory, rh_decoder


log = logging.get_obfslogger()

class BananaphoneTransport(BaseTransport):

    def __init__(self, transport_config):
        super(BananaphoneTransport, self).__init__()

        if transport_config.is_managed_mode and self.initiator:
            # managed client configured in handle_socks_args()
            return

        self.encode = self.encoder_factory()
        self.decode = self.decoder_factory()

    @classmethod
    def get_codec_factories(self, encodingSpec, modelName, corpus, order, abridged):
        if modelName == 'markov':
            args = [ corpus, order, abridged ]
        elif modelName == 'random':
            args = [ corpus ]
        else:
            log.error("BananaphoneTransport: unsupported model type")
            return

        # expensive model building operation
        log.warning("Bananaphone: building encoder %s model" % modelName)
        encoder_factory = rh_build_encoder_factory(encodingSpec, modelName, *args)
        decoder_factory = lambda: rh_decoder(encodingSpec)

        return (encoder_factory, decoder_factory)

    def handle_socks_args(self, args):
        # client case, managed mode
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

        encoder_factory, decoder_factory = self.get_codec_factories(self.encodingSpec, self.modelName, self.corpus, self.order, self.abridged)

        self.encode = encoder_factory()
        self.decode = decoder_factory()

    @classmethod
    def setup(cls, transport_config):

        if transport_config.is_managed_mode and cls.initiator:
            # managed client configured in handle_socks_args()
                return

        if transport_config.is_managed_mode:

            transport_options = transport_config.getServerTransportOptions()
            if not transport_options:
                log.error("BananaphoneTransport: must specify server transport options")
                return

            # XXX server case, managed mode is used
            for key in transport_options.keys():
                setattr(cls, key, transport_options[key])

            # BUG: modify bananaphone.py to
            # accept the abridged arg as boolean?
            if hasattr(cls,'abridged'):
                cls.abridged = '--abridged'
            else:
                # this is the only transport option which has a default value
                cls.abridged = None

        encoder_factory, decoder_factory = cls.get_codec_factories(cls.encodingSpec, cls.modelName, cls.corpus, cls.order, cls.abridged)
        cls.encoder_factory = staticmethod(encoder_factory)
        cls.decoder_factory = staticmethod(decoder_factory)


    @classmethod
    def get_public_server_options(cls, transport_options):
        """ Only tell BridgeDB about our encodingSpec transportOption
        """
        return dict(encodingSpec = transport_options['encodingSpec'])

    def circuitConnected(self):
        self.encoder = self.encode > self.circuit.downstream.write
        self.decoder = self.decode > self.circuit.upstream.write

    def receivedDownstream(self, data):
        self.decoder.send(data.read())

    def receivedUpstream(self, data):
        self.encoder.send(data.read())

    # XXX these options are mandatory
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

        # XXX client/server case, external mode
        cls.corpus       = args.corpus
        cls.encodingSpec = args.encodingSpec
        cls.modelName    = args.modelName
        cls.order        = args.order
        cls.abridged     = args.abridged
        super(BananaphoneTransport, cls).validate_external_mode_cli(args)


class BananaphoneClient(BananaphoneTransport):
    initiator = True

class BananaphoneServer(BananaphoneTransport):
    initiator = False

