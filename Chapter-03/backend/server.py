from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

class CORSRequestHandler(SimpleHTTPRequestHandler):
    """
    A simple HTTP request handler that adds CORS headers to every response.
    This is necessary to allow our frontend to communicate with the backend proxy
    server, which will run on a different port.
    """
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        return super().end_headers()

if __name__ == '__main__':
    # Change to the directory containing this script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Now, serve files from the ../frontend directory
    os.chdir('../frontend')
    
    port = 8000
    print(f"Frontend server starting at http://localhost:{port}")
    
    httpd = HTTPServer(('localhost', port), CORSRequestHandler)
    httpd.serve_forever()