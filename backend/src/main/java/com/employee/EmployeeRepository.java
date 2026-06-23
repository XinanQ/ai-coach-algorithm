package com.employee;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.Collection;
import java.util.List;
import java.util.Optional;

@Repository
public interface EmployeeRepository extends JpaRepository<Employee, Long> {

    List<Employee> findByOrganization_IdIn(Collection<Long> organizationIds);

    @Query("select e from Employee e left join fetch e.organization where e.id = :id")
    Optional<Employee> findByIdWithOrganization(Long id);
}