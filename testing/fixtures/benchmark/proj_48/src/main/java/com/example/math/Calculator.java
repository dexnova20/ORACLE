package com.example.math;

import static com.example.math.MathUtils.clamp;

public class Calculator {
    public int normalize(int value) {
        return clamp(value, 0, 100);
    }
}
