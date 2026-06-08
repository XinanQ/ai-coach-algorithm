package com.organization;

import com.organization.Organization;
import com.organization.Organization.OrgLevel;
import com.organization.OrganizationService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.URI;
import java.util.List;

@RestController
@RequestMapping("/api/admin/organizations")
public class OrganizationController {

    private final OrganizationService orgService;

    public OrganizationController(OrganizationService orgService){
        this.orgService = orgService;
    }

    @GetMapping
    public List<Organization> list(){
        return orgService.findAll();
    }

    @GetMapping("/tree")
    public List<Organization> tree(){
        return orgService.findTree();
    }

    @GetMapping("/{id}")
    public ResponseEntity<Organization> getById(@PathVariable Long id){
        return orgService.findById(id)
                .map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<Organization> create(@RequestBody Organization org, @RequestParam(required = false) Long parentId){
        if(parentId != null){
            orgService.findById(parentId).ifPresent(org::setParent);
        }
        Organization saved = orgService.save(org);
        return ResponseEntity.created(URI.create("/api/admin/organizations/" + saved.getId())).body(saved);
    }

    @PutMapping("/{id}")
    public ResponseEntity<Organization> update(@PathVariable Long id, @RequestBody Organization org, @RequestParam(required = false) Long parentId){
        return orgService.findById(id).map(existing ->{
            org.setId(id);
            if(parentId != null){
                orgService.findById(parentId).ifPresent(org::setParent);
            }
            Organization updated = orgService.save(org);
            return ResponseEntity.ok(updated);
        }).orElseGet(() -> ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        orgService.deleteById(id);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/by-level/{level}")
    public List<Organization> byLevel(@PathVariable OrgLevel level){
        return orgService.findByLevel(level);
    }
}
