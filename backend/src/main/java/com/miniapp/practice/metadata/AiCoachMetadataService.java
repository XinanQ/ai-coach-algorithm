package com.miniapp.practice.metadata;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.miniapp.practice.client.AiCoachProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

@Service
public class AiCoachMetadataService {

    private static final Logger log = LoggerFactory.getLogger(AiCoachMetadataService.class);
    private static final String CUSTOMER_PROFILES_FILE = "data/customer_profiles.json";
    private static final String BUSINESS_CONFIG_FILE = "configs/marketing_business_config.json";
    private static final String SCORING_CRITERIA_FILE = "data/marketing_scoring_criteria.json";
    private static final String MARKETING_CHUNKS_FILE = "data/marketing_chunks.json";

    private final AiCoachProperties aiCoachProperties;
    private final ObjectMapper objectMapper;

    public AiCoachMetadataService(AiCoachProperties aiCoachProperties, ObjectMapper objectMapper) {
        this.aiCoachProperties = aiCoachProperties;
        this.objectMapper = objectMapper;
    }

    public List<CustomerProfile> getProfiles() {
        Optional<JsonNode> root = readJson(CUSTOMER_PROFILES_FILE);
        if (root.isEmpty() || !root.get().isArray()) {
            return Collections.emptyList();
        }

        List<CustomerProfile> profiles = new ArrayList<>();
        for (JsonNode node : root.get()) {
            String sceneId = text(node, "scene_id");
            if (sceneId.isEmpty()) {
                log.warn("Skip AI coach customer profile without scene_id. profile={}", node);
                continue;
            }
            profiles.add(new CustomerProfile(
                    text(node, "customer_id"),
                    text(node, "customer_type"),
                    sceneId,
                    text(node, "scene_name"),
                    text(node, "personality"),
                    text(node, "concern"),
                    stringList(node.get("expected_intents")),
                    text(node, "opening_question"),
                    text(node, "followup_strategy"),
                    text(node, "difficulty_level"),
                    sha256(node.toString())
            ));
        }
        return profiles;
    }

    public Optional<CustomerProfile> findProfileBySceneId(String sceneId) {
        if (sceneId == null || sceneId.trim().isEmpty()) {
            return Optional.empty();
        }
        return getProfiles().stream()
                .filter(profile -> sceneId.equals(profile.getSceneId()))
                .findFirst();
    }

    public Optional<CustomerProfile> findProfileByCustomerId(String customerId) {
        if (customerId == null || customerId.trim().isEmpty()) {
            return Optional.empty();
        }
        return getProfiles().stream()
                .filter(profile -> customerId.equals(profile.getCustomerId()))
                .findFirst();
    }

    public List<MarketingKnowledgeChunk> getMarketingKnowledgeChunks() {
        Optional<JsonNode> root = readJson(MARKETING_CHUNKS_FILE);
        if (root.isEmpty()) {
            return Collections.emptyList();
        }

        JsonNode chunks = root.get().path("chunks");
        if (!chunks.isArray()) {
            log.warn("AI coach marketing chunks file has no chunks array.");
            return Collections.emptyList();
        }

        List<MarketingKnowledgeChunk> result = new ArrayList<>();
        for (JsonNode node : chunks) {
            String chunkId = text(node, "chunk_id");
            if (chunkId.isEmpty()) {
                log.warn("Skip AI coach marketing chunk without chunk_id.");
                continue;
            }
            result.add(new MarketingKnowledgeChunk(
                    chunkId,
                    text(node, "scene_id"),
                    text(node, "scene_name"),
                    text(node, "business_name"),
                    text(node, "title"),
                    text(node, "content"),
                    text(node, "tutor_view_text"),
                    text(node, "knowledge_type"),
                    text(node, "source_file"),
                    stringList(node.get("route_tags")),
                    text(node, "created_at"),
                    text(node, "compliance_status"),
                    text(node, "review_status"),
                    !node.has("enabled") || node.path("enabled").asBoolean(true)
            ));
        }
        return result;
    }

    public Optional<MarketingKnowledgeChunk> findMarketingKnowledgeChunkById(String chunkId) {
        if (chunkId == null || chunkId.trim().isEmpty()) {
            return Optional.empty();
        }
        return getMarketingKnowledgeChunks().stream()
                .filter(chunk -> chunkId.equals(chunk.getChunkId()))
                .findFirst();
    }

    public Optional<BusinessSceneMetadata> findBusinessConfigBySceneId(String sceneId) {
        if (sceneId == null || sceneId.trim().isEmpty()) {
            return Optional.empty();
        }

        Optional<JsonNode> root = readJson(BUSINESS_CONFIG_FILE);
        if (root.isEmpty()) {
            return Optional.empty();
        }

        JsonNode businesses = root.get().path("businesses");
        if (!businesses.isObject()) {
            return Optional.empty();
        }

        Iterator<Map.Entry<String, JsonNode>> businessIterator = businesses.fields();
        while (businessIterator.hasNext()) {
            Map.Entry<String, JsonNode> entry = businessIterator.next();
            JsonNode business = entry.getValue();
            JsonNode scenes = business.path("scenes");
            if (scenes.has(sceneId)) {
                return Optional.of(new BusinessSceneMetadata(
                        sceneId,
                        text(business, "business_name"),
                        scenes.path(sceneId).asText(""),
                        text(business, "folder"),
                        sceneRules(business.path("scene_rules"), sceneId)
                ));
            }
        }
        return Optional.empty();
    }

    public ScoringCriteriaMetadata findScoringCriteriaBySceneId(String sceneId) {
        if (sceneId == null || sceneId.trim().isEmpty()) {
            return ScoringCriteriaMetadata.empty(sceneId);
        }

        Optional<JsonNode> root = readJson(SCORING_CRITERIA_FILE);
        if (root.isEmpty()) {
            return ScoringCriteriaMetadata.empty(sceneId);
        }

        JsonNode criteria = root.get().path("criteria");
        if (!criteria.isArray()) {
            return ScoringCriteriaMetadata.empty(sceneId);
        }

        List<Map<String, Object>> matchedCriteria = new ArrayList<>();
        Set<String> mustPoints = new LinkedHashSet<>();
        String sceneName = "";
        for (JsonNode criterion : criteria) {
            if (!sceneId.equals(text(criterion, "scene_id"))) {
                continue;
            }
            if (criterion.has("enabled") && !criterion.path("enabled").asBoolean(true)) {
                continue;
            }
            if (sceneName.isEmpty()) {
                sceneName = text(criterion, "scene_name");
            }
            matchedCriteria.add(objectMapper.convertValue(criterion, new TypeReference<Map<String, Object>>() {
            }));
            for (String point : stringList(criterion.get("must_points"))) {
                if (!point.isEmpty()) {
                    mustPoints.add(point);
                }
            }
        }

        return new ScoringCriteriaMetadata(sceneId, sceneName, matchedCriteria, new ArrayList<>(mustPoints));
    }

    private Optional<JsonNode> readJson(String relativePath) {
        Path path = resolveDataDir().resolve(relativePath).normalize();
        if (!Files.isRegularFile(path)) {
            log.warn("AI coach metadata file not found. path={}", path.toAbsolutePath().normalize());
            return Optional.empty();
        }
        try {
            return Optional.of(objectMapper.readTree(path.toFile()));
        } catch (IOException ex) {
            log.error("Failed to read AI coach metadata file. path={}", path.toAbsolutePath().normalize(), ex);
            return Optional.empty();
        }
    }

    private Path resolveDataDir() {
        Path configured = Path.of(aiCoachProperties.getDataDir()).toAbsolutePath().normalize();
        if (Files.isDirectory(configured)) {
            return configured;
        }

        Path projectRootPath = Path.of("ai-coach-algorithm").toAbsolutePath().normalize();
        if (Files.isDirectory(projectRootPath)) {
            log.info("AI coach configured data-dir is not readable, using project-root data dir. configured={}, actual={}",
                    configured, projectRootPath);
            return projectRootPath;
        }

        log.warn("AI coach data-dir is not readable. configured={}", configured);
        return configured;
    }

    private List<Map<String, Object>> sceneRules(JsonNode rules, String sceneId) {
        if (!rules.isArray()) {
            return Collections.emptyList();
        }
        List<Map<String, Object>> result = new ArrayList<>();
        for (JsonNode rule : rules) {
            if (sceneId.equals(text(rule, "scene_id"))) {
                result.add(objectMapper.convertValue(rule, new TypeReference<Map<String, Object>>() {
                }));
            }
        }
        return result;
    }

    private String text(JsonNode node, String fieldName) {
        if (node == null || node.get(fieldName) == null || node.get(fieldName).isNull()) {
            return "";
        }
        return node.get(fieldName).asText("");
    }

    private List<String> stringList(JsonNode node) {
        if (node == null || !node.isArray()) {
            return Collections.emptyList();
        }
        List<String> result = new ArrayList<>();
        for (JsonNode item : node) {
            String value = item.asText("");
            if (!value.isEmpty()) {
                result.add(value);
            }
        }
        return result;
    }

    private String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder();
            for (byte b : hash) {
                hex.append(String.format("%02x", b));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is not available", ex);
        }
    }

    public static class CustomerProfile {
        private final String customerId;
        private final String customerType;
        private final String sceneId;
        private final String sceneName;
        private final String personality;
        private final String concern;
        private final List<String> expectedIntents;
        private final String openingQuestion;
        private final String followupStrategy;
        private final String difficultyLevel;
        private final String sourceProfileHash;

        public CustomerProfile(String customerId,
                               String customerType,
                               String sceneId,
                               String sceneName,
                               String personality,
                               String concern,
                               List<String> expectedIntents,
                               String openingQuestion,
                               String followupStrategy,
                               String difficultyLevel,
                               String sourceProfileHash) {
            this.customerId = customerId;
            this.customerType = customerType;
            this.sceneId = sceneId;
            this.sceneName = sceneName;
            this.personality = personality;
            this.concern = concern;
            this.expectedIntents = expectedIntents;
            this.openingQuestion = openingQuestion;
            this.followupStrategy = followupStrategy;
            this.difficultyLevel = difficultyLevel;
            this.sourceProfileHash = sourceProfileHash;
        }

        public String getCustomerId() {
            return customerId;
        }

        public String getCustomerType() {
            return customerType;
        }

        public String getSceneId() {
            return sceneId;
        }

        public String getSceneName() {
            return sceneName;
        }

        public String getPersonality() {
            return personality;
        }

        public String getConcern() {
            return concern;
        }

        public List<String> getExpectedIntents() {
            return expectedIntents;
        }

        public String getOpeningQuestion() {
            return openingQuestion;
        }

        public String getFollowupStrategy() {
            return followupStrategy;
        }

        public String getDifficultyLevel() {
            return difficultyLevel;
        }

        public String getSourceProfileHash() {
            return sourceProfileHash;
        }
    }

    public static class BusinessSceneMetadata {
        private final String sceneId;
        private final String businessName;
        private final String sceneName;
        private final String folder;
        private final List<Map<String, Object>> sceneRules;

        public BusinessSceneMetadata(String sceneId,
                                     String businessName,
                                     String sceneName,
                                     String folder,
                                     List<Map<String, Object>> sceneRules) {
            this.sceneId = sceneId;
            this.businessName = businessName;
            this.sceneName = sceneName;
            this.folder = folder;
            this.sceneRules = sceneRules;
        }

        public String getSceneId() {
            return sceneId;
        }

        public String getBusinessName() {
            return businessName;
        }

        public String getSceneName() {
            return sceneName;
        }

        public String getFolder() {
            return folder;
        }

        public List<Map<String, Object>> getSceneRules() {
            return sceneRules;
        }
    }

    public static class MarketingKnowledgeChunk {
        private final String chunkId;
        private final String sceneId;
        private final String sceneName;
        private final String businessName;
        private final String title;
        private final String content;
        private final String tutorViewText;
        private final String knowledgeType;
        private final String sourceFile;
        private final List<String> routeTags;
        private final String createdAt;
        private final String complianceStatus;
        private final String reviewStatus;
        private final boolean enabled;

        public MarketingKnowledgeChunk(String chunkId,
                                       String sceneId,
                                       String sceneName,
                                       String businessName,
                                       String title,
                                       String content,
                                       String tutorViewText,
                                       String knowledgeType,
                                       String sourceFile,
                                       List<String> routeTags,
                                       String createdAt,
                                       String complianceStatus,
                                       String reviewStatus,
                                       boolean enabled) {
            this.chunkId = chunkId;
            this.sceneId = sceneId;
            this.sceneName = sceneName;
            this.businessName = businessName;
            this.title = title;
            this.content = content;
            this.tutorViewText = tutorViewText;
            this.knowledgeType = knowledgeType;
            this.sourceFile = sourceFile;
            this.routeTags = routeTags;
            this.createdAt = createdAt;
            this.complianceStatus = complianceStatus;
            this.reviewStatus = reviewStatus;
            this.enabled = enabled;
        }

        public String getChunkId() {
            return chunkId;
        }

        public String getSceneId() {
            return sceneId;
        }

        public String getSceneName() {
            return sceneName;
        }

        public String getBusinessName() {
            return businessName;
        }

        public String getTitle() {
            return title;
        }

        public String getContent() {
            return content;
        }

        public String getTutorViewText() {
            return tutorViewText;
        }

        public String getKnowledgeType() {
            return knowledgeType;
        }

        public String getSourceFile() {
            return sourceFile;
        }

        public List<String> getRouteTags() {
            return routeTags;
        }

        public String getCreatedAt() {
            return createdAt;
        }

        public String getComplianceStatus() {
            return complianceStatus;
        }

        public String getReviewStatus() {
            return reviewStatus;
        }

        public boolean isEnabled() {
            return enabled;
        }
    }

    public static class ScoringCriteriaMetadata {
        private final String sceneId;
        private final String sceneName;
        private final List<Map<String, Object>> criteria;
        private final List<String> mustPoints;

        public ScoringCriteriaMetadata(String sceneId,
                                       String sceneName,
                                       List<Map<String, Object>> criteria,
                                       List<String> mustPoints) {
            this.sceneId = sceneId;
            this.sceneName = sceneName;
            this.criteria = criteria;
            this.mustPoints = mustPoints;
        }

        public static ScoringCriteriaMetadata empty(String sceneId) {
            return new ScoringCriteriaMetadata(sceneId, "", Collections.emptyList(), Collections.emptyList());
        }

        public String getSceneId() {
            return sceneId;
        }

        public String getSceneName() {
            return sceneName;
        }

        public List<Map<String, Object>> getCriteria() {
            return criteria;
        }

        public List<String> getMustPoints() {
            return mustPoints;
        }
    }
}
