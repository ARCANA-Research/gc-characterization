import jdk.jfr.Event;
import org.dacapo.harness.Callback;
import org.dacapo.harness.CommandLineArgs;

public class DacapoChopinCallback extends Callback {
  public class DaCapoJfr extends Event {
    public boolean roiStart = false;
    public boolean roiEnd = false;
  }

  static {
    System.loadLibrary("callback");
  }

  public DacapoChopinCallback(CommandLineArgs cla) {
    super(cla);
  }

  public void start(String benchmark) {
    if (!isWarmup()) {
      DaCapoJfr jfrEvent = new DaCapoJfr();
      jfrEvent.roiStart = true;
      jfrEvent.begin();
      jfrEvent.commit();
      startBenchmark();
    }
    super.start(benchmark);
  }

  public void stop(long duration) {
    super.stop(duration);
    if (!isWarmup()) {
      stopBenchmark();
      DaCapoJfr jfrEvent = new DaCapoJfr();
      jfrEvent.roiEnd = true;
      jfrEvent.begin();
      jfrEvent.commit();
    }
  }

  public native void startBenchmark();
  public native void stopBenchmark();
}
