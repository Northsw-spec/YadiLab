package main

import (
	"errors"
	"fmt"
	"io"
	"mime"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

type staticServer struct {
	root string
}

func newStaticServer(root string) (*staticServer, error) {
	abs, err := filepath.Abs(root)
	if err != nil {
		return nil, err
	}
	info, err := os.Stat(abs)
	if err != nil {
		return nil, err
	}
	if !info.IsDir() {
		return nil, fmt.Errorf("static root is not a directory: %s", abs)
	}
	real, err := filepath.EvalSymlinks(abs)
	if err != nil {
		return nil, err
	}
	return &staticServer{root: real}, nil
}

func securityHeaders(w http.ResponseWriter) {
	// Ajv is intentionally part of the pinned browser runtime and compiles the
	// shipped/imported JSON Schemas with new Function. Keep script loading
	// same-origin-only while allowing that validator code generation.
	w.Header().Set("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-eval'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'")
	w.Header().Set("Cross-Origin-Opener-Policy", "same-origin")
	w.Header().Set("Referrer-Policy", "no-referrer")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.Header().Set("X-Frame-Options", "DENY")
	w.Header().Set("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
	w.Header().Set("Cache-Control", "no-cache")
}

func suspiciousEscapedPath(r *http.Request) bool {
	raw := strings.ToLower(r.URL.EscapedPath())
	bad := []string{"%2e", "%2f", "%5c", "%00"}
	for _, token := range bad {
		if strings.Contains(raw, token) {
			return true
		}
	}
	return false
}

func (s *staticServer) resolve(requestPath string) (string, error) {
	if strings.ContainsRune(requestPath, '\x00') || strings.Contains(requestPath, "\\") {
		return "", errors.New("invalid path")
	}
	// r.URL.Path has already been percent-decoded exactly once by net/http.
	// A second decode would reinterpret literal "%2f" or "%2e" as path
	// separators/dot segments, aliasing a different resource.
	clean := filepath.Clean(filepath.FromSlash("/" + requestPath))
	rel := strings.TrimPrefix(clean, string(filepath.Separator))
	candidate := filepath.Join(s.root, rel)
	info, err := os.Stat(candidate)
	if err == nil && info.IsDir() {
		candidate = filepath.Join(candidate, "index.html")
	}
	real, err := filepath.EvalSymlinks(candidate)
	if err != nil {
		return "", err
	}
	relative, err := filepath.Rel(s.root, real)
	if err != nil {
		return "", err
	}
	if relative == ".." || strings.HasPrefix(relative, ".."+string(filepath.Separator)) {
		return "", errors.New("path escapes static root")
	}
	info, err = os.Stat(real)
	if err != nil {
		return "", err
	}
	if !info.Mode().IsRegular() {
		return "", errors.New("not a regular file")
	}
	return real, nil
}

func (s *staticServer) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	securityHeaders(w)
	if r.Method != http.MethodGet && r.Method != http.MethodHead {
		w.Header().Set("Allow", "GET, HEAD")
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if suspiciousEscapedPath(r) {
		http.Error(w, "invalid path", http.StatusBadRequest)
		return
	}
	path, err := s.resolve(r.URL.Path)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	f, err := os.Open(path)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	defer f.Close()
	info, err := f.Stat()
	if err != nil {
		http.NotFound(w, r)
		return
	}
	ct := mime.TypeByExtension(filepath.Ext(path))
	if filepath.Ext(path) == ".webmanifest" {
		ct = "application/manifest+json"
	}
	if ct != "" {
		w.Header().Set("Content-Type", ct)
	}
	if r.Method == http.MethodHead {
		w.Header().Set("Content-Length", fmt.Sprintf("%d", info.Size()))
		w.WriteHeader(http.StatusOK)
		return
	}
	http.ServeContent(w, r, info.Name(), info.ModTime(), io.NewSectionReader(f, 0, info.Size()))
}
