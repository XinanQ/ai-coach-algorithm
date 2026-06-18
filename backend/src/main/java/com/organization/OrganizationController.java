package com.organization;

import com.organization.Organization.OrgLevel;
import com.organization.dto.OrganizationCreateRequest;
import com.organization.dto.OrganizationResponse;
import com.organization.dto.OrganizationUpdateRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import com.employee.EmployeeService;

import java.net.URI;
import java.util.List;
import java.util.stream.Collectors;
import java.util.Map;

// 临时测试接口使用
import com.auth.CurrentUserContext;
//

@RestController
@RequestMapping("/api/admin/organizations")
public class OrganizationController {

    private final OrganizationService orgService;
    private final EmployeeService employeeService;

    public OrganizationController(OrganizationService orgService,
                                  EmployeeService employeeService){
        this.orgService = orgService;
        this.employeeService = employeeService;
    }

    private Map<Long, Long> getVisibleStaffCountMap() {
        return employeeService.countVisibleEmployeesByOrganizationId();
    }

    private Map<Long, Long> getVisibleAdminCountMap() {
        return employeeService.countVisibleAdminsByOrganizationId();
    }

    @GetMapping
    public List<OrganizationResponse> list(){
        Map<Long, Long> staffCountMap = getVisibleStaffCountMap();
        Map<Long, Long> adminCountMap = getVisibleAdminCountMap();

        return orgService.findVisibleOrganizations().stream()
                .map(org -> OrganizationResponse.from(org, staffCountMap, adminCountMap))
                .collect(Collectors.toList());
    }

    @GetMapping("/tree")
    public List<OrganizationResponse> tree(){
        Map<Long, Long> staffCountMap = getVisibleStaffCountMap();
        Map<Long, Long> adminCountMap = getVisibleAdminCountMap();

        return orgService.findVisibleTree().stream()
                .map(org -> OrganizationResponse.from(org, staffCountMap, adminCountMap))
                .collect(Collectors.toList());
    }

    @GetMapping("/{id}")
    public ResponseEntity<OrganizationResponse> getById(@PathVariable Long id){
        Map<Long, Long> staffCountMap = getVisibleStaffCountMap();
        Map<Long, Long> adminCountMap = getVisibleAdminCountMap();

        return orgService.findVisibleById(id)
                .map(org -> OrganizationResponse.from(org, staffCountMap, adminCountMap))
                .map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<OrganizationResponse> create(@RequestBody OrganizationCreateRequest request,
                                                       @RequestParam(required = false) Long parentId){
        Organization org = request.toOrganization();
        if(parentId != null){
            orgService.findById(parentId).ifPresent(org::setParent);
        }
        Organization saved = orgService.save(org);
        return ResponseEntity.created(URI.create("/api/admin/organizations/" + saved.getId()))
                .body(OrganizationResponse.from(saved));
    }

    @PutMapping("/{id}")
    public ResponseEntity<OrganizationResponse> update(@PathVariable Long id,
                                                       @RequestBody OrganizationUpdateRequest request,
                                                       @RequestParam(required = false) Long parentId){
        return orgService.findById(id).map(existing ->{
            request.applyTo(existing);
            existing.setId(id);
            if(parentId != null){
                orgService.findById(parentId).ifPresent(existing::setParent);
            }
            Organization updated = orgService.save(existing);
            return ResponseEntity.ok(OrganizationResponse.from(updated));
        }).orElseGet(() -> ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        orgService.deleteById(id);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/by-level/{level}")
    public List<OrganizationResponse> byLevel(@PathVariable OrgLevel level){
        Map<Long, Long> staffCountMap = getVisibleStaffCountMap();
        Map<Long, Long> adminCountMap = getVisibleAdminCountMap();

        return orgService.findVisibleByLevel(level).stream()
                .map(org -> OrganizationResponse.from(org, staffCountMap, adminCountMap))
                .collect(Collectors.toList());
    }

    // 临时测试接口使用
    @GetMapping("/visible-ids")
    public List<Long> getVisibleOrganizationIds() {
        Long organizationId = CurrentUserContext.getOrganizationId();
        return orgService.findSelfAndDescendantIds(organizationId);
    }
    //
}
