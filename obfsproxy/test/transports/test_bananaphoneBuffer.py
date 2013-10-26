#!/usr/bin/env python

import unittest
import twisted.trial.unittest


# TODO: proper unit tests and fix all the things. it works... i use this for testing.
import sys
sys.path.append("../../..")

from obfsproxy.transports.bananaphone_transport import BananaPhoneBuffer


def main():

    bananaBuffer = BananaPhoneBuffer()
    result1 = bananaBuffer.transcribeTo('the quick brown fox')
    print "result1 %s" % result1
    bananaBuffer.drain()

    #result1 = bananaBuffer.transcribeTo('the quick brown fox')
    #print "result1 %s" % result1
    #bananaBuffer.drain()

    result2 = bananaBuffer.transcribeFrom(result1)
    print "result2 %s" % result2
    bananaBuffer.drain()

    result3 = bananaBuffer.transcribeTo(result2)
    print "result3 %s" % result3


if __name__ == '__main__':
    main()
