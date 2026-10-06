import unittest
from pathlib import Path
import yaml

class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = yaml.safe_load(Path(".gitlab-ci.yml").read_text())

    def test_apply_uses_saved_plan_and_manual_gate(self):
        job = self.pipeline["apply"]
        self.assertEqual(job["when"], "manual")
        self.assertEqual(job["needs"], ["plan"])
        self.assertIn("deployment.tfplan", job["script"][0])
        self.assertFalse(job["allow_failure"])

    def test_cloud_jobs_require_protected_branch_and_oidc(self):
        cloud = self.pipeline[".cloud"]
        self.assertEqual(cloud["id_tokens"]["GITLAB_OIDC_TOKEN"]["aud"], "sts.amazonaws.com")
        self.assertIn('CI_COMMIT_REF_PROTECTED == "true"', cloud["rules"][0]["if"])
        for name in ("plan", "apply", "destroy"):
            self.assertEqual(self.pipeline[name]["extends"], ".cloud")
            self.assertEqual(self.pipeline[name]["resource_group"], "project26")

    def test_security_and_destroy_gates(self):
        self.assertIn("security", self.pipeline["stages"])
        self.assertEqual(self.pipeline["destroy"]["when"], "manual")
        self.assertIn("security", self.pipeline["destroy"]["needs"])
        self.assertEqual(self.pipeline["plan"]["artifacts"]["access"], "maintainer")

if __name__ == "__main__":
    unittest.main()
