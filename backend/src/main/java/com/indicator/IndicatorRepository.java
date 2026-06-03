package com.indicator;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface IndicatorRepository extends JpaRepository<Indicator, Long>,
        JpaSpecificationExecutor<Indicator> {

    boolean existsByCode(String code);

    boolean existsByCodeAndIdNot(String code, Long id);

    List<Indicator> findByParentId(Long parentId);
}
