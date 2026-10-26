package com.example.math;

public class MathUtils {
    public static int clamp(int v, int min, int max) {
        return Math.max(min, Math.min(max, v));
    }
}
