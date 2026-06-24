package com.points;

import java.util.List;

public interface PointsLogService {
    List<PointsLog> listVisible(Long reportId, Long employeeId);
}
