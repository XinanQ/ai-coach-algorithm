package com.points;

import com.performance.TaskResult;

public interface PointsCalculationService {

    /**
     * 审核通过后调用：按项目挂接配置算分并写入 points_logs。
     */
    PointsLog calculateOnApprove(TaskResult approvedReport);
}
