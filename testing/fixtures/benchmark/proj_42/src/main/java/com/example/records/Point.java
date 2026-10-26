package com.example.records;

public record Point(int x, int y) {
    public double distanceToOrigin() {
        return Math.sqrt(x * x + y * y);
    }
}
