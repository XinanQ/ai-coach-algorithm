<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1>组织架构管理</h1>
        <p>展示总行、省行、市行、支行、网点五级组织关系。</p>
      </div>
      <input v-model="keyword" class="field" placeholder="搜索机构" />
    </header>

    <section class="grid grid-2">
      <div class="panel">
        <div class="tree-title">
          <h2>五级组织树</h2>
          <span>{{ orgSummary }}</span>
        </div>
        <ul class="org-tree">
          <OrgNode
            v-for="node in filteredTree"
            :key="node.id"
            :node="node"
            :selected-id="selectedOrg?.id || ''"
            :expanded-ids="expandedIds"
            :depth="0"
            @select="selectedOrg = $event"
            @toggle="toggleNode"
          />
        </ul>
      </div>

      <div v-if="selectedOrg" class="panel detail-panel">
        <h2>机构详情</h2>
        <dl>
          <div>
            <dt>机构名称</dt>
            <dd>{{ selectedOrg.name }}</dd>
          </div>
          <div>
            <dt>层级</dt>
            <dd>{{ selectedOrg.level }}</dd>
          </div>
          <div>
            <dt>管理员</dt>
            <dd>{{ selectedOrg.manager }}</dd>
          </div>
          <div>
            <dt>直属下级</dt>
            <dd>{{ selectedOrg.children?.length || 0 }} 个</dd>
          </div>
          <div>
            <dt>网点人数</dt>
            <dd>{{ selectedOrg.staffCount || '按下级汇总' }}</dd>
          </div>
        </dl>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, ref } from 'vue'
import { getOrganizationTree } from '../api/organization'

const keyword = ref('')
const organizations = ref([])
const selectedOrg = ref(null)
const expandedIds = ref(new Set())

function includesKeyword(node, value) {
  return node.name.includes(value) || node.children?.some((child) => includesKeyword(child, value))
}

const filteredTree = computed(() => {
  if (!keyword.value.trim()) return organizations.value
  return organizations.value.filter((node) => includesKeyword(node, keyword.value.trim()))
})

function countNodes(nodes) {
  return nodes.reduce((sum, node) => sum + 1 + countNodes(node.children || []), 0)
}

function countOutlets(nodes) {
  return nodes.reduce(
    (sum, node) => sum + (node.level === '网点' ? 1 : 0) + countOutlets(node.children || []),
    0
  )
}

const orgSummary = computed(
  () => `${countNodes(organizations.value)} 个机构节点 · ${countOutlets(organizations.value)} 个网点`
)

function toggleNode(nodeId) {
  const nextExpandedIds = new Set(expandedIds.value)

  if (nextExpandedIds.has(nodeId)) {
    nextExpandedIds.delete(nodeId)
  } else {
    nextExpandedIds.add(nodeId)
  }

  expandedIds.value = nextExpandedIds
}

onMounted(async () => {
  organizations.value = await getOrganizationTree()
  selectedOrg.value = organizations.value[0]
})

const OrgNode = defineComponent({
  props: {
    node: { type: Object, required: true },
    selectedId: { type: String, required: true },
    expandedIds: { type: Object, required: true },
    depth: { type: Number, required: true }
  },
  emits: ['select', 'toggle'],
  setup(props, { emit }) {
    return () =>
      h('li', { class: 'tree-item' }, [
        h('div', { class: 'node-row', style: { paddingLeft: `${props.depth * 56}px` } }, [
          props.node.children?.length
            ? h(
                'button',
                {
                  class: ['toggle-button', props.expandedIds.has(props.node.id) ? 'open' : ''],
                  type: 'button',
                  onClick: () => {
                    emit('toggle', props.node.id)
                  }
                },
                props.expandedIds.has(props.node.id) ? '−' : '+'
              )
            : h('span', { class: 'toggle-spacer' }),
          h(
            'button',
            {
              class: ['org-node', props.node.id === props.selectedId ? 'active' : ''],
              onClick: () => emit('select', props.node)
            },
            [
              h('span', { class: 'node-name' }, props.node.name),
              h('span', { class: `level-pill level-${props.node.level}` }, props.node.level),
              h(
                'span',
                { class: 'node-meta' },
                props.node.level === '网点'
                  ? `${props.node.staffCount || 0} 人`
                  : `${props.node.children?.length || 0} 个下级`
              )
            ]
          )
        ]),
        props.node.children?.length && props.expandedIds.has(props.node.id)
          ? h(
              'ul',
              { class: 'tree-children' },
              props.node.children.map((child) =>
                h(OrgNode, {
                  key: child.id,
                  node: child,
                  selectedId: props.selectedId,
                  expandedIds: props.expandedIds,
                  depth: props.depth + 1,
                  onSelect: (node) => emit('select', node),
                  onToggle: (nodeId) => emit('toggle', nodeId)
                })
              )
            )
          : null
      ])
  }
})
</script>

<style>
.tree-title {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}

.tree-title h2 {
  margin: 0;
}

.tree-title span {
  color: #6b7280;
  font-size: 13px;
}

.org-tree,
.org-tree ul {
  margin: 0;
  padding-left: 0;
  list-style: none;
}

.org-tree {
  max-height: 680px;
  overflow: auto;
  padding: 4px 4px 4px 0;
}

.tree-item {
  position: relative;
}

.tree-children {
  position: relative;
  margin-top: 14px;
  margin-left: 0;
  padding-left: 0;
  padding-top: 2px;
}

.tree-children::before {
  content: none;
}

.tree-children > .tree-item::before {
  content: '';
  position: absolute;
  top: 20px;
  left: 10px;
  width: 36px;
  height: 1px;
  background: #d7dee8;
}

.tree-children > .tree-item + .tree-item {
  margin-top: 14px;
}

.node-row {
  display: flex;
  align-items: center;
  min-height: 40px;
  gap: 9px;
}

.toggle-button,
.toggle-spacer {
  width: 22px;
  height: 22px;
  flex: 0 0 22px;
}

.toggle-button {
  display: inline-grid;
  place-items: center;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  background: #fff;
  color: #334155;
  cursor: pointer;
  font-size: 15px;
  line-height: 1;
}

.toggle-button.open {
  border-color: #0f766e;
  color: #0f766e;
}

.org-node {
  min-width: 320px;
  height: 38px;
  padding: 0 12px;
  display: inline-flex;
  gap: 8px;
  align-items: center;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #fff;
  color: #111827;
  text-align: left;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.org-node.active {
  border-color: #0f766e;
  background: #ecfdf5;
}

.node-name {
  min-width: 92px;
  font-weight: 600;
}

.node-meta {
  margin-left: auto;
  color: #64748b;
  font-size: 12px;
}

.level-pill {
  padding: 1px 7px;
  border-radius: 999px;
  font-size: 12px;
}

.level-总行 {
  background: #fef2f2;
  color: #991b1b;
}

.level-省行 {
  background: #fff7ed;
  color: #9a3412;
}

.level-市行 {
  background: #eff6ff;
  color: #1d4ed8;
}

.level-支行 {
  background: #ecfdf5;
  color: #047857;
}

.level-网点 {
  background: #f5f3ff;
  color: #6d28d9;
}

.detail-panel dl {
  display: grid;
  gap: 14px;
}

.detail-panel dl div {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e5e7eb;
}

dt {
  color: #6b7280;
}

dd {
  margin: 0;
  color: #111827;
  font-weight: 600;
}
</style>
