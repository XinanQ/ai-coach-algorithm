package com.performance;

import com.performance.dto.ReportAttachmentUploadResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.Resource;
import org.springframework.core.io.UrlResource;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.net.MalformedURLException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;

@Service
public class ReportAttachmentService {

    private static final Set<String> ALLOWED_EXTENSIONS = Set.of(
            "pdf", "jpg", "jpeg", "png", "gif", "webp", "bmp",
            "doc", "docx", "xls", "xlsx", "ppt", "pptx",
            "txt", "csv", "zip", "rar", "7z"
    );

    private static final DateTimeFormatter MONTH_DIR = DateTimeFormatter.ofPattern("yyyyMM");

    private final Path uploadRoot;

    public ReportAttachmentService(@Value("${app.upload.report-dir:uploads/reports}") String uploadDir) {
        this.uploadRoot = Paths.get(uploadDir).toAbsolutePath().normalize();
    }

    public ReportAttachmentUploadResponse store(MultipartFile file) throws IOException {
        if (file == null || file.isEmpty()) {
            throw new IllegalArgumentException("请选择要上传的附件");
        }

        String originalName = sanitizeOriginalName(file.getOriginalFilename());
        String extension = extractExtension(originalName);
        if (extension.isEmpty() || !ALLOWED_EXTENSIONS.contains(extension)) {
            throw new IllegalArgumentException("不支持的附件格式，请上传常见文档或图片文件");
        }

        String monthDir = LocalDate.now().format(MONTH_DIR);
        Path targetDir = uploadRoot.resolve(monthDir);
        Files.createDirectories(targetDir);

        String storedName = UUID.randomUUID().toString().replace("-", "") + "_" + originalName;
        Path targetFile = targetDir.resolve(storedName).normalize();
        if (!targetFile.startsWith(uploadRoot)) {
            throw new IllegalArgumentException("非法的文件路径");
        }

        file.transferTo(targetFile.toFile());

        String url = "/api/admin/reports/attachments/files/" + monthDir + "/" + storedName;
        return new ReportAttachmentUploadResponse(url, originalName, file.getSize());
    }

    public Resource loadAsResource(String yearMonth, String fileName) throws MalformedURLException {
        validatePathSegment(yearMonth);
        validateStoredFileName(fileName);

        Path filePath = uploadRoot.resolve(yearMonth).resolve(fileName).normalize();
        if (!filePath.startsWith(uploadRoot) || !Files.exists(filePath)) {
            throw new IllegalArgumentException("附件不存在或已删除");
        }

        Resource resource = new UrlResource(filePath.toUri());
        if (!resource.exists() || !resource.isReadable()) {
            throw new IllegalArgumentException("附件无法读取");
        }
        return resource;
    }

    public String resolveDisplayName(String storedName) {
        if (storedName == null || storedName.isBlank()) {
            return "attachment";
        }
        int idx = storedName.indexOf('_');
        if (idx >= 0 && idx < storedName.length() - 1) {
            return storedName.substring(idx + 1);
        }
        return storedName;
    }

    public org.springframework.http.MediaType resolveMediaType(String fileName) {
        return switch (extractExtension(fileName)) {
            case "pdf" -> org.springframework.http.MediaType.APPLICATION_PDF;
            case "jpg", "jpeg" -> org.springframework.http.MediaType.IMAGE_JPEG;
            case "png" -> org.springframework.http.MediaType.IMAGE_PNG;
            case "gif" -> org.springframework.http.MediaType.IMAGE_GIF;
            case "webp" -> org.springframework.http.MediaType.parseMediaType("image/webp");
            case "bmp" -> org.springframework.http.MediaType.parseMediaType("image/bmp");
            case "txt" -> org.springframework.http.MediaType.TEXT_PLAIN;
            case "csv" -> org.springframework.http.MediaType.parseMediaType("text/csv");
            default -> org.springframework.http.MediaType.APPLICATION_OCTET_STREAM;
        };
    }

    private String sanitizeOriginalName(String originalFilename) {
        if (originalFilename == null || originalFilename.isBlank()) {
            return "attachment.bin";
        }
        String name = Paths.get(originalFilename).getFileName().toString().trim();
        name = name.replaceAll("[\\\\/:*?\"<>|]", "_");
        return name.isBlank() ? "attachment.bin" : name;
    }

    private String extractExtension(String fileName) {
        int dot = fileName.lastIndexOf('.');
        if (dot < 0 || dot == fileName.length() - 1) {
            return "";
        }
        return fileName.substring(dot + 1).toLowerCase(Locale.ROOT);
    }

    private void validatePathSegment(String value) {
        if (value == null || !value.matches("\\d{6}")) {
            throw new IllegalArgumentException("非法的附件路径");
        }
    }

    private void validateStoredFileName(String fileName) {
        if (fileName == null || fileName.isBlank() || fileName.contains("..") || fileName.contains("/")) {
            throw new IllegalArgumentException("非法的附件文件名");
        }
    }
}
