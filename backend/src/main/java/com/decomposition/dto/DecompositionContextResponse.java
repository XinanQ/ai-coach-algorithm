package com.decomposition.dto;

import java.util.List;

public class DecompositionContextResponse {

    private Long orgId;
    private String orgName;
    private String currentLevel;
    private String nextLevel;
    private List<ChildOrg> children;

    public Long getOrgId() { return orgId; }
    public void setOrgId(Long orgId) { this.orgId = orgId; }
    public String getOrgName() { return orgName; }
    public void setOrgName(String orgName) { this.orgName = orgName; }
    public String getCurrentLevel() { return currentLevel; }
    public void setCurrentLevel(String currentLevel) { this.currentLevel = currentLevel; }
    public String getNextLevel() { return nextLevel; }
    public void setNextLevel(String nextLevel) { this.nextLevel = nextLevel; }
    public List<ChildOrg> getChildren() { return children; }
    public void setChildren(List<ChildOrg> children) { this.children = children; }

    public static class ChildOrg {
        private Long id;
        private String name;
        private String level;

        public Long getId() { return id; }
        public void setId(Long id) { this.id = id; }
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public String getLevel() { return level; }
        public void setLevel(String level) { this.level = level; }
    }
}
