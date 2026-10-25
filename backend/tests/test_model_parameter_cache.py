"""Behavioral guard for model-parameter deletion; requires Node and frontend npm deps."""

import shutil
import subprocess
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCRIPT = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const frontend = path.join(process.cwd(), 'frontend');
const ts = require(path.join(frontend, 'node_modules/typescript'));
const { ref, reactive, computed } = require(path.join(frontend, 'node_modules/vue'));
const component = fs.readFileSync(path.join(frontend, 'src/views/system/model/ModelForm.vue'), 'utf8');
const script = component.match(/<script[^>]*>([\s\S]*?)<\/script>/)[1];
const ast = ts.createSourceFile('ModelForm.ts', script, ts.ScriptTarget.Latest, true);
const names = new Set([
  'modelForm', 'modelRef', 'advancedSetting', 'tempConfigMap', 'curId',
  'currentSupplier', 'modelList', 'initForm', 'handleParamsDel', 'supplierChang',
  'formatAdvancedSetting', 'baseModelChange', 'getSupplierDomain', 'getModelDefaultArgs',
  'submitModel',
]);
const selected = ast.statements.filter(statement => ts.isVariableStatement(statement) &&
  statement.declarationList.declarations.some(declaration => names.has(declaration.name.getText(ast))));
assert.equal(selected.length, names.size, 'all tested component declarations must be extracted');
const js = ts.transpileModule(selected.map(statement => statement.getText(ast)).join('\n'), {
  compilerOptions: { target: ts.ScriptTarget.ES2020 },
}).outputText;
const suppliers = [
  {id: 15, type: 'openai', model_config: {0: {api_domain: 'http://example.test/v1',
    common_args: [{key: 'temperature', val: 0.6}], model_options: []}}},
  {id: 16, type: 'openai', model_config: {0: {api_domain: 'http://other.test/v1',
    common_args: [{key: 'temperature', val: 0.3}], model_options: []}}},
];
let emitted;
const getSupplier = id => suppliers.find(supplier => supplier.id === id);
const api = new Function('ref', 'reactive', 'computed', 'get_supplier', 'base_model_options', 'emits',
  js + '\nreturn {modelForm, modelRef, advancedSetting, initForm, handleParamsDel, supplierChang, baseModelChange, submitModel};'
)(ref, reactive, computed, getSupplier, id => getSupplier(id).model_config[0].model_options,
  (event, payload) => {assert.equal(event, 'submit'); emitted = payload;});
api.modelRef.value = {clearValidate() {}, validate(callback) {callback(true);}};
const original = {supplier: 15, base_model: 'gpt-4.1', model_type: 0, config_list: [
  {id: 1, name: 'Temperature', key: 'temperature', val: 0.8},
  {id: 2, name: 'Token limit', key: 'max_tokens', val: 4096},
]};
const untouched = JSON.stringify(original);
const select = (supplierId, model) => {
  if (supplierId !== api.modelForm.supplier) api.supplierChang(getSupplier(supplierId));
  api.modelForm.base_model = model;
  api.baseModelChange(model);
};
const submit = () => {api.submitModel(); return emitted.config_list;};
api.initForm(original);
select(15, 'gpt-4o-mini');
select(16, 'gpt-4.1');
select(15, 'gpt-4.1');
assert.deepEqual(submit(), [
  {key: 'temperature', name: 'Temperature', val: 0.8},
  {key: 'max_tokens', name: 'Token limit', val: 4096},
], 'switching without deleting preserves model configuration');
const deleteAll = process.argv[1] === 'all';
const deleted = deleteAll ? [...api.advancedSetting.value] : [api.advancedSetting.value[1]];
for (const item of deleted) api.handleParamsDel(item);
const expected = deleteAll ? [] : [{key: 'temperature', name: 'Temperature', val: 0.8}];
assert.deepEqual(submit(), expected, 'deletion updates the emitted payload immediately');
select(15, 'gpt-4o-mini');
assert.deepEqual(submit(), [{key: 'temperature', name: 'temperature', val: 0.6}], 'other model unchanged');
select(16, 'gpt-4.1');
assert.deepEqual(submit(), [{key: 'temperature', name: 'temperature', val: 0.3}], 'other supplier unchanged');
select(15, 'gpt-4.1');
assert.deepEqual(submit(), expected, 'deleted parameters must stay deleted after switching back');
assert.equal(JSON.stringify(original), untouched, 'deleting must not mutate loaded input configuration');
"""


class ModelParameterCacheTestCase(unittest.TestCase):
    def check_deletion(self, mode: str) -> None:
        if not shutil.which("node"):
            self.skipTest("Node is required for the frontend behavior guard")
        if not (
            PROJECT_ROOT / "frontend/node_modules/typescript/package.json"
        ).exists():
            self.skipTest("Run npm install in frontend before this behavior guard")
        result = subprocess.run(
            ["node", "-e", SCRIPT, mode],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_deleted_parameter_stays_deleted_after_switching_models(self) -> None:
        self.check_deletion("one")

    def test_deleting_all_parameters_stays_empty_after_switching_models(self) -> None:
        self.check_deletion("all")


if __name__ == "__main__":
    unittest.main()
