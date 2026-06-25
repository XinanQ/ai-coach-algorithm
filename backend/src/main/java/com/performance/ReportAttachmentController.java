package com.performance;

import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

@RestController
@RequestMapping("/api/admin/reports/attachments")
public class ReportAttachmentController {

    private final ReportAttachmentService attachmentService;

    public ReportAttachmentController(ReportAttachmentService attachmentService) {
        this.attachmentService = attachmentService;
    }

    @GetMapping("/files/{yearMonth}/{fileName:.+}")
    public ResponseEntity<Resource> download(@PathVariable String yearMonth,
                                             @PathVariable String fileName,
                                             @RequestParam(defaultValue = "false") boolean download) throws IOException {
        Resource resource = attachmentService.loadAsResource(yearMonth, fileName);
        String displayName = attachmentService.resolveDisplayName(fileName);
        MediaType mediaType = attachmentService.resolveMediaType(displayName);
        String encodedName = URLEncoder.encode(displayName, StandardCharsets.UTF_8).replace("+", "%20");
        String dispositionType = download ? "attachment" : "inline";

        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, dispositionType + "; filename*=UTF-8''" + encodedName)
                .contentType(mediaType)
                .body(resource);
    }
}
