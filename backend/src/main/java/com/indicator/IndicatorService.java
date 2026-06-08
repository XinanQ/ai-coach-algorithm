package com.indicator;

import com.indicator.dto.*;
import com.task.Task;
import org.springframework.data.domain.Page;

import java.util.List;

public interface IndicatorService {

    // 1.1.3.1 指标库
    Page<IndicatorResponse> listLibrary(String businessLine, Boolean enabled,
                                        String category, String keyword, int page, int size);

    IndicatorResponse getLibraryById(Long id);

    IndicatorResponse createLibrary(IndicatorCreateRequest req);

    IndicatorResponse updateLibrary(Long id, IndicatorUpdateRequest req);

    IndicatorResponse updateLibraryStatus(Long id, IndicatorStatusRequest req);

    void deleteLibrary(Long id);

    // 1.1.3.2 分解 / 催办（A）
    List<Indicator> findChildren(Long parentId);

    Indicator decompose(Long id, Indicator child);

    void remind(Long id, String message);

    List<Task> findReminders(Long indicatorId);
}
