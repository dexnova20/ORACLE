package com.example.repo;

import java.util.ArrayList;
import java.util.List;

public class UserRepository implements Repository<String> {
    private final List<String> storage = new ArrayList<>();

    @Override
    public List<String> findAll() {
        return new ArrayList<>(storage);
    }

    @Override
    public void save(String item) {
        storage.add(item);
    }
}
