package com.auth;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.Collection;
import java.util.List;

@Repository
public interface UserAccountRepository extends JpaRepository<UserAccount, Long> {

    Optional<UserAccount> findByEmployeeNo(String employeeNo);

    Optional<UserAccount> findByEmployeeId(Long employeeId);

    List<UserAccount> findByEmployeeIdIn(Collection<Long> employeeIds);
}