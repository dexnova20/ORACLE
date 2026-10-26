package com.example.api;

public class Application {
    public static void main(String[] args) {
        UserService service = new UserService();
        System.out.println(service.getGreeting("World"));
    }
}
