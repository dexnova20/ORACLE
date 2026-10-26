package com.example.tree;

import java.util.ArrayList;
import java.util.List;

public class TreeNode {
    private final String value;
    private final List<TreeNode> children = new ArrayList<>();

    public TreeNode(String value) {
        this.value = value;
    }

    public static class Builder {
        private String value;

        public Builder setValue(String val) {
            this.value = val;
            return this;
        }

        public TreeNode build() {
            return new TreeNode(this.value);
        }
    }
}
