package com.employee;


import org.apache.poi.ss.usermodel.*;
import org.apache.poi.ss.usermodel.WorkbookFactory;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class ExcelUtil {

    public static List<Employee> parseEmployees(InputStream in) throws IOException {
        List<Employee> list = new ArrayList<>();
        try (Workbook wb = WorkbookFactory.create(in)) {
            Sheet sheet = wb.getSheetAt(0);
            DataFormatter formatter = new DataFormatter();
            boolean first = true;
            Map<String, Integer> headerIndex = new HashMap<>();
            for (Row row : sheet) {
                if (first) {
                    first = false;
                    for (Cell cell : row) {
                        String header = formatter.formatCellValue(cell).trim().toLowerCase();
                        headerIndex.put(header, cell.getColumnIndex());
                    }
                    continue;
                }
                if (row == null || row.getPhysicalNumberOfCells() == 0) {
                    continue;
                }
                Employee e = new Employee();
                e.setName(getString(row, headerIndex, formatter, "name"));
                String ageStr = getString(row, headerIndex, formatter, "age");
                if (ageStr != null && !ageStr.isEmpty()) {
                    try { e.setAge(Integer.valueOf(ageStr)); } catch (Exception ex) { }
                }
                e.setDepartment(getString(row, headerIndex, formatter, "department"));
                e.setEmail(getString(row, headerIndex, formatter, "email"));
                e.setPosition(getString(row, headerIndex, formatter, "position"));
                String orgId = getString(row, headerIndex, formatter, "organizationid", "organization_id", "organization id", "orgid");
                if (orgId != null && !orgId.isEmpty()) {
                    try { e.setOrganizationId(Long.valueOf(orgId)); } catch (Exception ex) { }
                }
                e.setLevel(getString(row, headerIndex, formatter, "level"));
                String isNew = getString(row, headerIndex, formatter, "isnew", "is_new", "new");
                if (isNew != null) e.setIsNew("1".equals(isNew) || "true".equalsIgnoreCase(isNew));
                e.setWorkType(getString(row, headerIndex, formatter, "worktype", "work_type"));
                String isAdmin = getString(row, headerIndex, formatter, "isadmin", "is_admin", "admin");
                if (isAdmin != null) e.setIsAdmin("1".equals(isAdmin) || "true".equalsIgnoreCase(isAdmin));
                String isInProject = getString(row, headerIndex, formatter, "isinproject", "is_in_project", "inproject", "in_project");
                if (isInProject != null) e.setIsInProject("1".equals(isInProject) || "true".equalsIgnoreCase(isInProject));
                list.add(e);
            }
        } catch (Exception ex) {
            throw new IOException("Failed to parse employee Excel file", ex);
        }
        return list;
    }

    public static byte[] employeesToExcel(List<Employee> list) throws IOException {
        try (XSSFWorkbook wb = new XSSFWorkbook(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            Sheet sheet = wb.createSheet("Employees");
            int rowIdx = 0;
            Row header = sheet.createRow(rowIdx++);
            header.createCell(0).setCellValue("name");
            header.createCell(1).setCellValue("age");
            header.createCell(2).setCellValue("department");
            header.createCell(3).setCellValue("email");
            header.createCell(4).setCellValue("position");
            header.createCell(5).setCellValue("organizationId");
            header.createCell(6).setCellValue("level");
            header.createCell(7).setCellValue("isNew");
            header.createCell(8).setCellValue("workType");
            header.createCell(9).setCellValue("isAdmin");
            header.createCell(10).setCellValue("isInProject");

            for (Employee e : list) {
                Row r = sheet.createRow(rowIdx++);
                r.createCell(0).setCellValue(nullSafe(e.getName()));
                r.createCell(1).setCellValue(e.getAge() == null ? "" : String.valueOf(e.getAge()));
                r.createCell(2).setCellValue(nullSafe(e.getDepartment()));
                r.createCell(3).setCellValue(nullSafe(e.getEmail()));
                r.createCell(4).setCellValue(nullSafe(e.getPosition()));
                r.createCell(5).setCellValue(e.getOrganizationId() == null ? "" : String.valueOf(e.getOrganizationId()));
                r.createCell(6).setCellValue(nullSafe(e.getLevel()));
                r.createCell(7).setCellValue(e.getIsNew() == null ? "" : String.valueOf(e.getIsNew()));
                r.createCell(8).setCellValue(nullSafe(e.getWorkType()));
                r.createCell(9).setCellValue(e.getIsAdmin() == null ? "" : String.valueOf(e.getIsAdmin()));
                r.createCell(10).setCellValue(e.getIsInProject() == null ? "" : String.valueOf(e.getIsInProject()));
            }

            wb.write(out);
            return out.toByteArray();
        }
    }

    private static String getString(Row row, Map<String, Integer> headerIndex, DataFormatter formatter, String... names) {
        for (String name : names) {
            Integer idx = headerIndex.get(name.toLowerCase());
            if (idx != null) {
                Cell c = row.getCell(idx);
                if (c != null) {
                    String value = formatter.formatCellValue(c).trim();
                    if (!value.isEmpty()) {
                        return value;
                    }
                }
            }
        }
        return null;
    }

    private static String nullSafe(String s) { return s == null ? "" : s; }
}
