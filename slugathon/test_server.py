import time
import subprocess

from twisted.internet import reactor
import py

import Client

class TestServer(object):
    def setup_class(cls):
        subprocess.Popen("python Server.py &", shell=True)
        time.sleep(1)
    
    def test_startup(self):
        self.client = Client.Client(username="unittest", password="unittest")
        def1 = self.client.connect()
        def1.addCallback(self.connected)
        def1.addErrback(self.failure)
        reactor.run()
    
    def connected(self, perspective):
        print "connected", self, perspective
        def1 = perspective.callRemote("get_name", "foo")
        def1.addCallback(self.success)
        def1.addErrback(self.failure)
    
    def success(self, name):
        assert name == "unittest"
        reactor.stop()
    
    def failure(self, error):
        print error
        reactor.stop()
        py.test.fail()
    
    def teardown_class(cls):
        subprocess.call(["pkill", "-f", "python.*Server.py"])
