package com.decomposition;

import com.decomposition.dto.DecompositionContextResponse;
import com.decomposition.dto.DecompositionListResponse;
import com.decomposition.dto.DecompositionSaveRequest;

import java.util.List;
import java.util.Map;

public interface DecompositionService {
    List<DecompositionListResponse> list(String ownerRole, Long currentOrgId, Long projectId);
    Map<String, Object> save(DecompositionSaveRequest request);
    DecompositionContextResponse getContext();
    DecompositionListResponse findById(Long id);
}
