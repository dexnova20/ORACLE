package com.example.app;

import org.apache.commons.lang3.StringUtils;

public class StringProcessor {
    public boolean check(String text) {
        return StringUtils.isNotBlank(text);
    }
}
