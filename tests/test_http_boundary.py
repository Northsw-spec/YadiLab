"""Real socket checks for the loopback HTTP trust boundary."""
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from test_model import example


class LocalHTTPBoundaryTests(unittest.TestCase):
    def test_server_refuses_non_loopback_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "127.0.0.1"):
                LabHTTPServer(("0.0.0.0", 0), ProjectStore(Path(directory)))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name))
        self.server = LabHTTPServer(("127.0.0.1", 0), self.store)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host = f"127.0.0.1:{self.server.server_port}"
        self.origin = f"http://{self.host}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=4)
        self.tmp.cleanup()

    def request(self, method, path, headers=(), data=None):
        payload = None if data is None else json.dumps(data).encode("utf-8")
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port,
                                                timeout=5)
        connection.putrequest(method, path, skip_host=True)
        for key, value in headers:
            connection.putheader(key, value)
        if payload is not None:
            connection.putheader("Content-Type", "application/json")
            connection.putheader("Content-Length", str(len(payload)))
        connection.endheaders(payload)
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_exact_host_and_same_origin_allow_browser_and_local_client(self):
        for headers in ((("Host", self.host),),
                        (("Host", self.host), ("Origin", self.origin),
                         ("Sec-Fetch-Site", "same-origin"))):
            with self.subTest(headers=headers):
                status, _, _ = self.request("GET", "/api/health", headers)
                self.assertEqual(status, 200)
        payload = {"filename": "local", "project": example(), "expectedSha256": None}
        status, _, _ = self.request("POST", "/api/save", (("Host", self.host),), payload)
        self.assertEqual(status, 200)
        self.assertEqual(self.store.read("local")["project"], example())

    def test_static_modules_are_explicitly_allowed_without_directory_access(self):
        headers = (("Host", self.host),)
        for path in ("/ui/dom.js", "/services/api.js",
                     "/features/projects/persistence.js"):
            with self.subTest(path=path):
                status, response_headers, body = self.request("GET", path, headers)
                self.assertEqual(status, 200)
                self.assertIn(response_headers["Content-Type"].split(";", 1)[0],
                              ("text/javascript", "application/javascript"))
                self.assertIn(b"export ", body)
        for path in ("/ui/", "/services/", "/features/", "/features/projects/",
                     "/features/projects/../projects/persistence.js",
                     "/ui/../services/api.js",
                     "/network_core/server.py", "/docs/QUALITY_IMPROVEMENT_PLAN.md"):
            with self.subTest(path=path):
                status, _, body = self.request("GET", path, headers)
                self.assertEqual(status, 404)
                self.assertNotIn(b"export ", body)

    def test_reject_bad_host_before_project_read_or_write(self):
        self.store.save("private", example())
        bad_hosts = ("evil.example", "localhost", "127.0.0.1",
                     f"127.0.0.1:{self.server.server_port + 1}",
                     f"127.0.0.1:{self.server.server_port}.evil.example")
        for host in bad_hosts:
            with self.subTest(host=host):
                status, _, body = self.request("GET", "/api/projects/private",
                                               (("Host", host),))
                self.assertEqual(status, 403)
                self.assertNotIn(b"private", body)
                status, _, _ = self.request("POST", "/api/save", (("Host", host),),
                                             {"filename": "intruder", "project": example(),
                                              "expectedSha256": None})
                self.assertEqual(status, 403)
        for hosts in ((), (("Host", self.host), ("Host", self.host))):
            with self.subTest(hosts=hosts):
                self.assertEqual(self.request("GET", "/api/projects/private", hosts)[0],
                                 403)
        self.assertFalse(self.store.path("intruder").exists())

    def test_reject_cross_origin_and_fetch_metadata_without_origin(self):
        self.store.save("private", example())
        for origin in ("http://evil.example", "null", "https://" + self.host,
                       self.origin + "/", f"http://127.0.0.1:{self.server.server_port + 1}"):
            with self.subTest(origin=origin):
                headers = (("Host", self.host), ("Origin", origin))
                self.assertEqual(self.request("GET", "/api/projects/private", headers)[0],
                                 403)
                self.assertEqual(self.request("POST", "/api/save", headers,
                                              {"filename": "intruder", "project": example(),
                                               "expectedSha256": None})[0], 403)
        for site in ("cross-site", "same-site"):
            headers = (("Host", self.host), ("Sec-Fetch-Site", site))
            self.assertEqual(self.request("GET", "/api/projects/private", headers)[0], 403)
            self.assertEqual(self.request("POST", "/api/save", headers,
                                          {"filename": "intruder", "project": example(),
                                           "expectedSha256": None})[0], 403)
        self.assertFalse(self.store.path("intruder").exists())

    def test_no_origin_form_cannot_write_and_duplicate_origin_is_rejected(self):
        payload = json.dumps({"filename": "intruder", "project": example(),
                              "expectedSha256": None}).encode("utf-8")
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port,
                                                timeout=5)
        connection.putrequest("POST", "/api/save", skip_host=True)
        connection.putheader("Host", self.host)
        connection.putheader("Content-Type", "text/plain")
        connection.putheader("Content-Length", str(len(payload)))
        connection.endheaders(payload)
        response = connection.getresponse()
        self.assertEqual(response.status, 415)
        response.read()
        connection.close()
        headers = (("Host", self.host), ("Origin", self.origin),
                   ("Origin", self.origin))
        self.assertEqual(self.request("POST", "/api/save", headers,
                                      {"filename": "intruder", "project": example(),
                                       "expectedSha256": None})[0], 403)
        self.assertFalse(self.store.path("intruder").exists())

    def test_preflight_does_not_enable_cors(self):
        headers = (("Host", self.host), ("Origin", "http://evil.example"),
                   ("Access-Control-Request-Method", "POST"))
        status, response_headers, _ = self.request("OPTIONS", "/api/save", headers)
        self.assertEqual(status, 403)
        self.assertNotIn("Access-Control-Allow-Origin", response_headers)
