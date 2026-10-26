package com.example.io;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.CompletableFuture;
import javax.net.ssl.SSLSocket;

public class FileHandler {
    public CompletableFuture<Void> handle(Path path) {
        return CompletableFuture.completedFuture(null);
    }
}
