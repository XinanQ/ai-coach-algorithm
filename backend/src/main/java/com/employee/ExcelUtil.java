package com.employee;

import com.employee.Employee;
import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.xssf.usermodel.XSSFSheet;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

public class ExcelUtil {

    public static List<Employee> parseEmployees(InputStream in) throws IOException {
        List<Employee> list = new ArrayList<>();
        try (XSSFWorkbook wb = new XSSFWorkbook(in)) {
            XSSFSheet sheet = wb.getSheetAt(0);
            boolean first = true;
            for (Row row : sheet) {
                if (first) { first = false; continue; }
                Employee e = new Employee();
                e.setName(getString(row,0));
                String ageStr = getString(row,1);
                if(ageStr != null && !ageStr.isEmpty()){
                    try{ e.setAge(Integer.valueOf(ageStr)); } catch(Exception ex){ }
                }
                e.setDepartment(getString(row,2));
                e.setEmail(getString(row,3));
                e.setPosition(getString(row,4));
                String orgId = getString(row,5);
                if(orgId != null && !orgId.isEmpty()){ try{ e.setOrganizationId(Long.valueOf(orgId)); }catch(Exception ex){} }
                e.setLevel(getString(row,6));
                String isNew = getString(row,7);
                if(isNew != null) e.setIsNew("1".equals(isNew) || "true".equalsIgnoreCase(isNew));
                e.setWorkType(getString(row,8));
                String isAdmin = getString(row,9);
                if(isAdmin != null) e.setIsAdmin("1".equals(isAdmin) || "true".equalsIgnoreCase(isAdmin));
                String isInProject = getString(row,10);
                if(isInProject != null) e.setIsInProject("1".equals(isInProject) || "true".equalsIgnoreCase(isInProject));
                list.add(e);
            }
        }
        return list;
    }

    public static byte[] employeesToExcel(List<Employee> list) throws IOException {
        try (XSSFWorkbook wb = new XSSFWorkbook(); ByteArrayOutputStream out = new ByteArrayOutputStream()){
            XSSFSheet sheet = wb.createSheet("Employees");
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

    private static String getString(Row row, int idx){
        if(row == null) return null;
        Cell c = row.getCell(idx);
        if(c == null) return null;
        switch(c.getCellType()){
            case STRING: return c.getStringCellValue();
            case NUMERIC: return String.valueOf((long)c.getNumericCellValue());
            case BOOLEAN: return String.valueOf(c.getBooleanCellValue());
            default: return c.toString();
        }
    }

    private static String nullSafe(String s){ return s == null ? "" : s; }
}
