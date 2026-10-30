import importlib.util
from pathlib import Path
import unittest
spec = importlib.util.spec_from_file_location('progress', Path(__file__).resolve().parents[1] / 'skills/querying-noibu-data/scripts/dashboard_progress.py')
progress = importlib.util.module_from_spec(spec)
spec.loader.exec_module(progress)

class DashboardProgress(unittest.TestCase):
    def connected(self):
        return dict(mode='visitor-connected', eligibility='allowed', projectId='site', savedVersionId='version', deploymentStatus='succeeded', liveUrl='https://example.com', dependenciesReady=True, sourceReady=True, buildPassed=True, hostedInitialReadPassed=True, hostedRefreshPassed=True, filtersPassed=True, accountSeparationPassed=True, expiredAuthorizationPassed=True)

    def test_native_and_direct_readiness(self):
        value = self.connected()
        self.assertTrue(progress.assess(value)['ready'])
        value.update(connectionMethod='direct-oauth', nativeConnectorStatus='missing', directOAuthSupported=True)
        self.assertEqual(progress.assess(value)['next'], 'verify-token-refresh')
        value['tokenRefreshPassed'] = True
        self.assertTrue(progress.assess(value)['ready'])
        for flag in ('filtersPassed', 'accountSeparationPassed', 'expiredAuthorizationPassed'):
            self.assertFalse(progress.assess({**value, flag: False})['ready'])

    def test_no_bypass(self):
        value = {**self.connected(), 'connectionMethod':'direct-oauth', 'directOAuthSupported':True}
        for native in ('available', 'unknown', 'denied'):
            self.assertFalse(progress.assess({**value, 'nativeConnectorStatus':native})['ready'])
        self.assertFalse(progress.assess({**value, 'nativeConnectorStatus':'missing', 'securityRestriction':True})['ready'])

    def test_snapshot_unchanged(self):
        value = {**self.connected(), 'mode':'persistent-snapshot', 'totalsVerified':True, 'persistenceReady':True, 'persistenceReadbackPassed':True}
        self.assertEqual(progress.assess(value)['state'], 'persistent-verified')
        self.assertFalse(progress.assess({**value, 'eligibility':'denied'})['ready'])

if __name__ == '__main__':
    unittest.main()
