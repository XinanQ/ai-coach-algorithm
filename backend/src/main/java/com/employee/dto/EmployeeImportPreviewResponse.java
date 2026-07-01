package com.employee.dto;

import java.util.ArrayList;
import java.util.List;

public class EmployeeImportPreviewResponse {

    private List<EmployeeImportPreviewItem> items = new ArrayList<>();
    private int validCount;
    private int invalidCount;

    public List<EmployeeImportPreviewItem> getItems() {
        return items;
    }

    public void setItems(List<EmployeeImportPreviewItem> items) {
        this.items = items;
    }

    public int getValidCount() {
        return validCount;
    }

    public void setValidCount(int validCount) {
        this.validCount = validCount;
    }

    public int getInvalidCount() {
        return invalidCount;
    }

    public void setInvalidCount(int invalidCount) {
        this.invalidCount = invalidCount;
    }
}
