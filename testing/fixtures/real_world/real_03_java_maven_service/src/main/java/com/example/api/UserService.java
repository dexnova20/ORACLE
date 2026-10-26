package com.example.api;

public class UserService {
    public String getGreeting(String name) {
        if (name == null) {
            return "Hello, Guest";
        }
        return "Hello, " + name;
    }
}
