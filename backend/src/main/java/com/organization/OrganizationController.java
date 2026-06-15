package com.organization;

import com.organization.Organization.OrgLevel;
import com.organization.dto.OrganizationCreateRequest;
import com.organization.dto.OrganizationResponse;
import com.organization.dto.OrganizationUpdateRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.URI;
import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/admin/organizations")
public class OrganizationController {

    private final OrganizationService orgService;

    public OrganizationController(OrganizationService orgService){
        this.orgService = orgService;
    }

    @GetMapping
    public List<OrganizationResponse> list(){
        return orgService.findAll().stream()
                .map(OrganizationResponse::from)
                .collect(Collectors.toList());
    }

    @GetMapping("/tree")
    public List<OrganizationResponse> tree(){
        return orgService.findTree().stream()
                .map(OrganizationResponse::from)
                .collect(Collectors.toList());
    }

    @GetMapping("/{id}")
    public ResponseEntity<OrganizationResponse> getById(@PathVariable Long id){
        return orgService.findById(id)
                .map(OrganizationResponse::from)
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
        return orgService.findByLevel(level).stream()
                .map(OrganizationResponse::from)
                .collect(Collectors.toList());
    }
}
