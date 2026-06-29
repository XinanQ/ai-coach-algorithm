package com.miniapp.script;

import com.miniapp.script.dto.MiniScriptDetailResponse;
import com.miniapp.script.dto.MiniScriptSummaryResponse;
import org.springframework.stereotype.Service;

import java.util.Arrays;
import java.util.List;

/**
 * 小程序话术库业务服务。
 *
 * 接入 AI 算法服务或正式话术库数据源，
 * 可以优先替换本 Service 内部的数据生成逻辑，Controller 接口路径和响应结构保持不变。
 */
@Service
public class MiniScriptService {

    private static final String SOURCE_RULE_BASED = "RULE_BASED";

    /**
     * 获取小程序话术库列表。
     *
     * 前端期望 data 直接是数组，因此 Controller 会直接返回 List<MiniScriptSummaryResponse>。
     */
    public List<MiniScriptSummaryResponse> getScripts() {
        return Arrays.asList(
                new MiniScriptSummaryResponse(
                        "s1",
                        "理财产品风险揭示",
                        "稳健型客户风险揭示",
                        Arrays.asList("合规表达", "风险提示"),
                        "06/12"
                ),
                new MiniScriptSummaryResponse(
                        "s2",
                        "存款推荐",
                        "流动性需求应对",
                        Arrays.asList("异议处理"),
                        "06/10"
                )
        );
    }

    /**
     * 获取小程序话术详情。
     *
     * @param scriptId 话术 ID，例如 s1 / s2
     * @return 话术详情
     */
    public MiniScriptDetailResponse getScriptDetail(String scriptId) {
        if ("s2".equals(scriptId)) {
            return buildLiquidityScript();
        }

        return buildRiskDisclosureScript(scriptId);
    }

    private MiniScriptDetailResponse buildRiskDisclosureScript(String scriptId) {
        return new MiniScriptDetailResponse(
                scriptId == null || scriptId.isBlank() ? "s1" : scriptId,
                "理财产品风险揭示",
                "稳健型客户风险揭示",
                Arrays.asList("合规表达", "风险提示"),
                "您关注本金安全是非常合理的。这款产品主要投资于高评级债券与货币工具，整体波动较低，过去三年最大回撤控制在较小范围；同时它支持灵活赎回，兼顾收益与流动性。",
                "practice-risk-disclosure-001",
                "这款产品风险不大，主要投债券，历史上波动也比较小，您可以放心一些。",
                SOURCE_RULE_BASED
        );
    }

    private MiniScriptDetailResponse buildLiquidityScript() {
        return new MiniScriptDetailResponse(
                "s2",
                "存款推荐",
                "流动性需求应对",
                Arrays.asList("异议处理"),
                "如果您担心后续临时用钱，我们可以优先选择支持灵活支取或分层配置的产品方案。这样既能保留一部分资金流动性，也可以让暂时不用的资金获得相对稳健的收益。",
                "practice-high-net-worth-needs-001",
                "您可以先放一部分活期，剩下的做收益高一点的产品，这样用钱也比较方便。",
                SOURCE_RULE_BASED
        );
    }
}
