import jenkins.model.*
import hudson.security.*

def password = System.getenv('JENKINS_ADMIN_PASSWORD')
if (!password) return

def instance = Jenkins.getInstance()
def realm = instance.getSecurityRealm()
if (!(realm instanceof HudsonPrivateSecurityRealm)) return

def user = realm.getUser('admin')
if (!user) return

user.addProperty(HudsonPrivateSecurityRealm.Details.fromPlainPassword(password))
user.save()
instance.save()
