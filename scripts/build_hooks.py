# scripts/build_hooks.py
"""Build hooks for development environment setup - 修正版本"""
import os
import sys
import logging
from pathlib import Path

# 设置详细的调试日志
logging.basicConfig(
    level=logging.DEBUG,
    format='[BUILD_HOOK] %(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('build_hook_debug.log', mode='a')  # 追加模式
    ]
)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("BUILD HOOK MODULE LOADED")
logger.info(f"Python version: {sys.version}")
logger.info(f"Working directory: {os.getcwd()}")
logger.info(f"Script path: {__file__}")
logger.info("=" * 60)


def create_test_symlink():
    """在可编辑安装时创建测试模块的软链接"""
    logger.info("create_test_symlink() called")

    # 打印调试信息到控制台
    print("\n" + "=" * 60)
    print("🔧 BUILD HOOK: Test Symlink Setup")
    print("=" * 60)

    try:
        project_root = Path(__file__).parent.parent
        src_dir = project_root / "src" / "rhosocial"
        test_src = project_root / "tests" / "rhosocial" / "activerecord_test"
        symlink_target = src_dir / "activerecord_test"

        print(f"📁 Project root: {project_root}")
        print(f"📁 Source: {test_src}")
        print(f"📁 Target: {symlink_target}")
        print(f"🔍 Source exists: {test_src.exists()}")
        print(f"🔍 Target exists: {symlink_target.exists()}")

        # 详细记录到日志
        logger.info(f"Project paths:")
        logger.info(f"  project_root: {project_root}")
        logger.info(f"  test_src: {test_src}")
        logger.info(f"  symlink_target: {symlink_target}")
        logger.info(f"  test_src.exists(): {test_src.exists()}")
        logger.info(f"  symlink_target.exists(): {symlink_target.exists()}")

        # 检查源目录
        if not test_src.exists():
            print(f"❌ Test directory not found: {test_src}")
            logger.error(f"Test directory not found: {test_src}")
            return False

        # 如果目标已存在，检查状态
        if symlink_target.exists():
            if symlink_target.is_symlink():
                try:
                    real_target = symlink_target.resolve()
                    expected_target = test_src.resolve()
                    if real_target == expected_target:
                        print("✅ Symlink already exists and points to correct location")
                        logger.info("Symlink already exists and points to correct location")
                        return True
                    else:
                        print(f"⚠️ Symlink points to wrong location: {real_target} != {expected_target}")
                        logger.warning(f"Symlink points to wrong location: {real_target} != {expected_target}")
                        print("🔄 Removing incorrect symlink...")
                        symlink_target.unlink()
                except Exception as e:
                    print(f"⚠️ Error checking symlink: {e}")
                    logger.error(f"Error checking symlink: {e}")
                    return False
            else:
                print(f"⚠️ Target exists but is not a symlink: {symlink_target}")
                logger.warning(f"Target exists but is not a symlink: {symlink_target}")
                return False

        # 确保目标目录存在
        try:
            src_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured src_dir exists: {src_dir}")
        except Exception as e:
            print(f"❌ Failed to create src directory: {e}")
            logger.error(f"Failed to create src directory: {e}")
            return False

        # 尝试创建软链接
        print("🔗 Attempting to create symlink...")
        logger.info("Attempting to create symlink")

        try:
            # 使用相对路径
            relative_path = os.path.relpath(test_src.resolve(), src_dir.resolve())

            logger.info(f"Creating symlink with relative path: {relative_path}")
            print(f"🔗 Using relative path: {relative_path}")

            symlink_target.symlink_to(relative_path, target_is_directory=True)

            # 验证软链接
            if symlink_target.exists() and symlink_target.is_dir():
                print(f"✅ Created test symlink: {symlink_target} -> {test_src}")
                print("✅ Symlink verification successful")
                logger.info(f"Successfully created symlink: {symlink_target} -> {test_src}")
                return True
            else:
                print("❌ Symlink created but verification failed")
                logger.error("Symlink created but verification failed")
                return False

        except OSError as e:
            print(f"❌ Failed to create symlink: {e}")
            logger.error(f"Failed to create symlink: {e}")

            # 提供解决方案
            print("\n🛠️ Manual solution:")
            manual_cmd = f"ln -sf {test_src} {symlink_target}"
            print(f"   {manual_cmd}")
            logger.error(f"Manual command: {manual_cmd}")
            return False

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logger.error(f"Unexpected error: {e}")
        return False
    finally:
        print("=" * 60 + "\n")


# 导入hatch接口
try:
    from hatchling.builders.hooks.plugin.interface import BuildHookInterface

    logger.info("Successfully imported BuildHookInterface")
except ImportError as e:
    logger.error(f"Failed to import BuildHookInterface: {e}")
    BuildHookInterface = None


class CustomBuildHook(BuildHookInterface):
    """自定义构建钩子 - 修正版本"""

    def __init__(self, *args, **kwargs):
        logger.info(f"CustomBuildHook.__init__ called with args={args}, kwargs={kwargs}")
        super().__init__(*args, **kwargs)
        logger.info(f"CustomBuildHook initialized, target_name: {getattr(self, 'target_name', 'UNKNOWN')}")

    def initialize(self, version, build_data):
        """初始化构建钩子 - 修正版本检查逻辑"""
        logger.info("=" * 50)
        logger.info("🚀 CustomBuildHook.initialize() called!")
        logger.info(f"  version: {repr(version)}")
        logger.info(f"  build_data: {build_data}")
        logger.info(f"  target_name: {getattr(self, 'target_name', 'UNKNOWN')}")

        # 打印到控制台以便观察
        print(f"\n🔧 BUILD HOOK TRIGGERED!")
        print(f"   Version: {repr(version)}")
        print(f"   Target: {getattr(self, 'target_name', 'UNKNOWN')}")
        print(f"   Build Data Keys: {list(build_data.keys()) if build_data else 'None'}")

        # 🔥 关键修复：检查version参数而不是target_name
        if version == "editable":
            print("✅ Detected editable installation - proceeding with symlink creation")
            logger.info("Detected editable installation via version parameter")
            success = create_test_symlink()
            if success:
                print("✅ Symlink setup completed successfully")
                logger.info("Symlink setup completed successfully")
            else:
                print("❌ Symlink setup failed")
                logger.error("Symlink setup failed")
        else:
            print(f"ℹ️  Non-editable build (version={repr(version)}) - skipping symlink creation")
            logger.info(f"Non-editable build (version={repr(version)}) - skipping symlink creation")

        logger.info("CustomBuildHook.initialize() completed")
        logger.info("=" * 50)


# 如果直接运行脚本，也执行软链接创建
if __name__ == "__main__":
    logger.info("Running build_hooks.py directly")
    print("🚀 Running build hook directly...")
    create_test_symlink()

__all__ = ['CustomBuildHook']