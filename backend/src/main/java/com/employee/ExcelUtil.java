package com.employee;


import com.organization.Organization;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.ss.util.CellRangeAddressList;
import org.apache.poi.ss.usermodel.WorkbookFactory;
import org.apache.poi.xssf.usermodel.XSSFDataValidation;
import org.apache.poi.xssf.usermodel.XSSFDataValidationConstraint;
import org.apache.poi.xssf.usermodel.XSSFDataValidationHelper;
import org.apache.poi.xssf.usermodel.XSSFSheet;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class ExcelUtil {

    /** 导入模板列（不含层级，导入时自动推断） */
    private static final String[] IMPORT_TEMPLATE_HEADERS = {
            "姓名", "邮箱", "职务", "所属机构", "年龄", "部门",
            "员工类型", "是否新员工", "是否管理员", "是否参与项目"
    };

    /** 导出列（含自动推断后的层级，只读参考） */
    private static final String[] EXPORT_HEADERS = {
            "姓名", "邮箱", "职务", "所属机构", "年龄", "部门", "层级",
            "员工类型", "是否新员工", "是否管理员", "是否参与项目"
    };

    private static final int COL_ORG = 3;
    private static final int COL_AGE = 4;
    private static final int COL_DEPT = 5;
    private static final int COL_WORK_TYPE = 6;
    private static final int COL_IS_NEW = 7;
    private static final int COL_IS_ADMIN = 8;
    private static final int COL_IS_IN_PROJECT = 9;

    /** 导出比导入多一列「层级」，后续列索引 +1 */
    private static final int EXP_COL_LEVEL = 6;
    private static final int EXP_COL_WORK_TYPE = 7;
    private static final int EXP_COL_IS_NEW = 8;
    private static final int EXP_COL_IS_ADMIN = 9;
    private static final int EXP_COL_IS_IN_PROJECT = 10;

    public static List<ParsedEmployeeRow> parseEmployeeRows(InputStream in) throws IOException {
        List<ParsedEmployeeRow> list = new ArrayList<>();
        try (Workbook wb = WorkbookFactory.create(in)) {
            Sheet sheet = resolveImportSheet(wb);
            DataFormatter formatter = new DataFormatter();
            boolean first = true;
            Map<String, Integer> headerIndex = new HashMap<>();
            for (Row row : sheet) {
                if (first) {
                    first = false;
                    for (Cell cell : row) {
                        String header = formatter.formatCellValue(cell).trim();
                        String normalized = normalizeHeaderKey(header);
                        headerIndex.put(normalized, cell.getColumnIndex());
                    }
                    continue;
                }
                if (row == null || isRowEmpty(row, formatter)) {
                    continue;
                }

                Employee employee = parseEmployeeFromRow(row, headerIndex, formatter);
                list.add(new ParsedEmployeeRow(row.getRowNum() + 1, employee));
            }
        } catch (Exception ex) {
            throw new IOException("Failed to parse employee Excel file", ex);
        }
        return list;
    }

    /** 优先读「员工导入」Sheet；避免误读隐藏的 lists / 机构对照 等辅助 Sheet。 */
    private static Sheet resolveImportSheet(Workbook wb) {
        Sheet byName = wb.getSheet("员工导入");
        if (byName != null) {
            return byName;
        }
        for (int i = 0; i < wb.getNumberOfSheets(); i++) {
            if (wb.isSheetHidden(i) || wb.isSheetVeryHidden(i)) {
                continue;
            }
            Sheet candidate = wb.getSheetAt(i);
            Row header = candidate.getRow(0);
            if (header != null && rowHasEmployeeHeader(header)) {
                return candidate;
            }
        }
        return wb.getSheetAt(0);
    }

    private static boolean rowHasEmployeeHeader(Row row) {
        DataFormatter formatter = new DataFormatter();
        for (Cell cell : row) {
            String normalized = normalizeHeaderKey(formatter.formatCellValue(cell).trim());
            if ("name".equals(normalized)) {
                return true;
            }
        }
        return false;
    }

    public static List<Employee> parseEmployees(InputStream in) throws IOException {
        List<Employee> list = new ArrayList<>();
        for (ParsedEmployeeRow row : parseEmployeeRows(in)) {
            list.add(row.employee());
        }
        return list;
    }

    public static byte[] buildImportTemplate(List<Organization> organizations) throws IOException {
        try (XSSFWorkbook wb = new XSSFWorkbook(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            XSSFSheet sheet = wb.createSheet("员工导入");
            int rowIdx = 0;

            Row header = sheet.createRow(rowIdx++);
            for (int i = 0; i < IMPORT_TEMPLATE_HEADERS.length; i++) {
                header.createCell(i).setCellValue(IMPORT_TEMPLATE_HEADERS[i]);
            }

            String exampleOrgName = organizations.isEmpty() ? "南京市行" : nullSafe(organizations.get(0).getName());
            Row example = sheet.createRow(rowIdx++);
            example.createCell(0).setCellValue("示例员工");
            example.createCell(1).setCellValue("example@bank.com");
            example.createCell(2).setCellValue("客户经理");
            example.createCell(COL_ORG).setCellValue(exampleOrgName);
            example.createCell(COL_AGE).setCellValue(28);
            example.createCell(COL_DEPT).setCellValue("个人金融部");
            example.createCell(COL_WORK_TYPE).setCellValue("外勤");
            example.createCell(COL_IS_NEW).setCellValue("是");
            example.createCell(COL_IS_ADMIN).setCellValue("否");
            example.createCell(COL_IS_IN_PROJECT).setCellValue("否");

            for (int i = 0; i < 20; i++) {
                sheet.createRow(rowIdx++);
            }

            XSSFSheet listsSheet = wb.createSheet("lists");
            int orgCount = 0;
            for (Organization org : organizations) {
                ensureCell(listsSheet, orgCount, 0).setCellValue(nullSafe(org.getName()));
                orgCount++;
            }
            if (orgCount == 0) {
                ensureCell(listsSheet, 0, 0).setCellValue("南京市行");
                orgCount = 1;
            }
            ensureCell(listsSheet, 0, 1).setCellValue("内勤");
            ensureCell(listsSheet, 1, 1).setCellValue("外勤");
            ensureCell(listsSheet, 0, 2).setCellValue("是");
            ensureCell(listsSheet, 1, 2).setCellValue("否");

            Name orgListName = wb.createName();
            orgListName.setNameName("OrgList");
            orgListName.setRefersToFormula("'lists'!$A$1:$A$" + orgCount);
            Name workTypeListName = wb.createName();
            workTypeListName.setNameName("WorkTypeList");
            workTypeListName.setRefersToFormula("'lists'!$B$1:$B$2");
            Name yesNoListName = wb.createName();
            yesNoListName.setNameName("YesNoList");
            yesNoListName.setRefersToFormula("'lists'!$C$1:$C$2");

            wb.setSheetVisibility(wb.getSheetIndex(listsSheet), SheetVisibility.HIDDEN);

            int firstDataRow = 1;
            int lastDataRow = 500;
            addNamedListValidation(sheet, firstDataRow, lastDataRow, COL_ORG, "所属机构", "OrgList");
            addNamedListValidation(sheet, firstDataRow, lastDataRow, COL_WORK_TYPE, "员工类型", "WorkTypeList");
            addNamedListValidation(sheet, firstDataRow, lastDataRow, COL_IS_NEW, "是否新员工", "YesNoList");
            addNamedListValidation(sheet, firstDataRow, lastDataRow, COL_IS_ADMIN, "是否管理员", "YesNoList");
            addNamedListValidation(sheet, firstDataRow, lastDataRow, COL_IS_IN_PROJECT, "是否参与项目", "YesNoList");

            for (int i = 0; i < IMPORT_TEMPLATE_HEADERS.length; i++) {
                sheet.autoSizeColumn(i);
            }

            wb.setActiveSheet(wb.getSheetIndex(sheet));
            wb.setSelectedTab(wb.getSheetIndex(sheet));

            wb.write(out);
            return out.toByteArray();
        }
    }

    private static Cell ensureCell(Sheet sheet, int rowIdx, int colIdx) {
        Row row = sheet.getRow(rowIdx);
        if (row == null) {
            row = sheet.createRow(rowIdx);
        }
        Cell cell = row.getCell(colIdx);
        if (cell == null) {
            cell = row.createCell(colIdx);
        }
        return cell;
    }

    /**
     * POI 5.2.x + Excel OOXML：setSuppressDropDownArrow(true) 才会显示下拉箭头
     * （false 会写入 showDropDown=1，反而隐藏箭头）。
     */
    private static void addNamedListValidation(XSSFSheet sheet,
                                               int firstRow,
                                               int lastRow,
                                               int columnIndex,
                                               String title,
                                               String namedRange) {
        XSSFDataValidationHelper helper = new XSSFDataValidationHelper(sheet);
        XSSFDataValidationConstraint constraint =
                (XSSFDataValidationConstraint) helper.createFormulaListConstraint(namedRange);
        CellRangeAddressList addressList = new CellRangeAddressList(firstRow, lastRow, columnIndex, columnIndex);
        XSSFDataValidation validation = (XSSFDataValidation) helper.createValidation(constraint, addressList);
        validation.setEmptyCellAllowed(true);
        validation.setShowErrorBox(true);
        validation.setErrorStyle(DataValidation.ErrorStyle.STOP);
        validation.createErrorBox(title, "请从下拉列表中选择");
        validation.setShowPromptBox(true);
        validation.createPromptBox(title, "点击单元格，使用右侧下拉箭头或 Option+↓ 选择");
        validation.setSuppressDropDownArrow(true);
        sheet.addValidationData(validation);
    }

    public static byte[] employeesToExcel(List<Employee> list) throws IOException {
        try (XSSFWorkbook wb = new XSSFWorkbook(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            Sheet sheet = wb.createSheet("员工导入");
            int rowIdx = 0;
            Row header = sheet.createRow(rowIdx++);
            for (int i = 0; i < EXPORT_HEADERS.length; i++) {
                header.createCell(i).setCellValue(EXPORT_HEADERS[i]);
            }

            for (Employee e : list) {
                Row r = sheet.createRow(rowIdx++);
                r.createCell(0).setCellValue(nullSafe(e.getName()));
                r.createCell(1).setCellValue(nullSafe(e.getEmail()));
                r.createCell(2).setCellValue(nullSafe(e.getPosition()));
                r.createCell(COL_ORG).setCellValue(
                        e.getOrganization() == null ? "" : nullSafe(e.getOrganization().getName()));
                r.createCell(COL_AGE).setCellValue(e.getAge() == null ? "" : String.valueOf(e.getAge()));
                r.createCell(COL_DEPT).setCellValue(nullSafe(e.getDepartment()));
                String exportLevel = e.getLevel();
                if (exportLevel == null || exportLevel.isBlank()) {
                    exportLevel = EmployeeLevelResolver.inferLevel(e.getIsAdmin(), e.getOrganization());
                }
                r.createCell(EXP_COL_LEVEL).setCellValue(formatLevelForExport(exportLevel));
                r.createCell(EXP_COL_WORK_TYPE).setCellValue(nullSafe(e.getWorkType()));
                r.createCell(EXP_COL_IS_NEW).setCellValue(formatBooleanForExport(e.getIsNew()));
                r.createCell(EXP_COL_IS_ADMIN).setCellValue(formatBooleanForExport(e.getIsAdmin()));
                r.createCell(EXP_COL_IS_IN_PROJECT).setCellValue(formatBooleanForExport(e.getIsInProject()));
            }

            for (int i = 0; i < EXPORT_HEADERS.length; i++) {
                sheet.autoSizeColumn(i);
            }

            wb.write(out);
            return out.toByteArray();
        }
    }

    private static Employee parseEmployeeFromRow(Row row,
                                                 Map<String, Integer> headerIndex,
                                                 DataFormatter formatter) {
        Employee e = new Employee();
        e.setName(getString(row, headerIndex, formatter, "name"));
        String ageStr = getString(row, headerIndex, formatter, "age");
        if (ageStr != null && !ageStr.isEmpty()) {
            try {
                e.setAge(Integer.valueOf(ageStr));
            } catch (Exception ex) {
                // preview will validate
            }
        }
        e.setDepartment(getString(row, headerIndex, formatter, "department"));
        e.setEmail(getString(row, headerIndex, formatter, "email"));
        e.setPosition(getString(row, headerIndex, formatter, "position"));

        Organization organization = new Organization();
        String orgId = getString(row, headerIndex, formatter, "organizationid");
        String orgName = getString(row, headerIndex, formatter, "organizationname");
        if (orgId != null && !orgId.isEmpty()) {
            try {
                organization.setId(Long.valueOf(orgId));
            } catch (Exception ex) {
                // preview will validate
            }
        }
        if (orgName != null && !orgName.isEmpty()) {
            organization.setName(orgName);
        }
        if (organization.getId() != null || organization.getName() != null) {
            e.setOrganization(organization);
        }

        // level 由 EmployeeLevelResolver 在保存前自动推断，Excel 中的层级列（若有）忽略
        e.setIsNew(parseBoolean(getString(row, headerIndex, formatter, "isnew")));
        e.setWorkType(getString(row, headerIndex, formatter, "worktype"));
        e.setIsAdmin(parseBoolean(getString(row, headerIndex, formatter, "isadmin")));
        e.setIsInProject(parseBoolean(getString(row, headerIndex, formatter, "isinproject")));
        return e;
    }

    private static String normalizeHeaderKey(String header) {
        if (header == null) {
            return "";
        }
        String value = header.trim().toLowerCase();
        return switch (value) {
            case "姓名" -> "name";
            case "邮箱" -> "email";
            case "职务" -> "position";
            case "机构id", "机构_id", "所属机构id", "organizationid", "organization_id", "organization id", "orgid" -> "organizationid";
            case "所属机构", "机构名称", "机构", "organizationname", "organization_name", "organization name", "orgname" -> "organizationname";
            case "年龄" -> "age";
            case "部门" -> "department";
            case "员工类型", "内勤外勤" -> "worktype";
            case "是否新员工", "新员工" -> "isnew";
            case "是否管理员", "管理员" -> "isadmin";
            case "是否参与项目", "参与项目" -> "isinproject";
            case "层级", "level" -> "level";
            default -> value.replace(" ", "");
        };
    }

    private static Boolean parseBoolean(String val) {
        if (val == null || val.isBlank()) {
            return null;
        }
        String s = val.trim().toLowerCase();
        if ("1".equals(s) || "true".equals(s) || "是".equals(s) || "yes".equals(s) || "y".equals(s)) {
            return true;
        }
        if ("0".equals(s) || "false".equals(s) || "否".equals(s) || "no".equals(s) || "n".equals(s)) {
            return false;
        }
        return null;
    }

    private static boolean isRowEmpty(Row row, DataFormatter formatter) {
        if (row == null) {
            return true;
        }
        for (Cell cell : row) {
            if (cell != null && !formatter.formatCellValue(cell).trim().isEmpty()) {
                return false;
            }
        }
        return true;
    }

    private static String getString(Row row, Map<String, Integer> headerIndex, DataFormatter formatter, String... names) {
        for (String name : names) {
            Integer idx = headerIndex.get(name);
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

    private static String formatBooleanForExport(Boolean value) {
        if (value == null) {
            return "";
        }
        return value ? "是" : "否";
    }

    private static String formatLevelForExport(String level) {
        if (level == null || level.isBlank()) {
            return "";
        }
        return switch (level.trim().toUpperCase()) {
            case "EMPLOYEE" -> "员工";
            case "OUTLET" -> "网点";
            case "BRANCH" -> "支行";
            case "CITY", "HEAD", "HEADQUARTERS", "PROVINCE" -> "市行";
            default -> level.trim();
        };
    }

    private static String nullSafe(String s) {
        return s == null ? "" : s;
    }

    public record ParsedEmployeeRow(int rowIndex, Employee employee) {
    }
}
