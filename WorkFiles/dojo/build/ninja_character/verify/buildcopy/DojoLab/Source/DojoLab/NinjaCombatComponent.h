// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "NinjaCombatComponent.generated.h"

class ACharacter;
class UAnimMontage;
class UAnimSequenceBase;
class UInputAction;
class UInputComponent;
class UInputMappingContext;

/** What the ninja is doing right now. One move at a time; Block is a separate hold (see bBlocking). */
UENUM(BlueprintType)
enum class ENinjaCombatMove : uint8
{
	None,
	LightAttack,
	HeavyAttack,
	Dodge,
	Kunai,
	Shunshin,
	HitReaction,
	/** The pack's acrobatic throw, split off onto its own key so 1 stays the quick grounded one. */
	KunaiAerial
};

/** Which way a dodge goes, taken from the move input at the moment Left Alt is pressed. */
UENUM(BlueprintType)
enum class ENinjaDodgeDirection : uint8
{
	Back,
	Forward,
	Left,
	Right
};

/** Where a hit came from, in the victim's own space. Picks one of the pack's four 0.4 s flinches. */
UENUM(BlueprintType)
enum class ENinjaHitDirection : uint8
{
	Front,
	Back,
	Left,
	Right
};

/**
 * One throw of the 1 chain (Cody, 2026-09-21: pressing 1 again within ~2 s of a throw does the NEXT throw - the left-waist
 * backhand, then the right-pocket rising throw, then the backhand again - so spamming 1 flows). Times are clip times, in seconds
 * at play rate 1. Animation and IdleAnimation must share one timeline (make_throw_rising.py builds them that way), so the
 * chain times and ReleaseTime hold for whichever of the two is playing.
 *
 * A press during this throw hands over to the next one inside [ChainOutTime, ChainOutEndTime] of THIS clip, entering the next
 * throw's Animation at NextStartTime + (time past ChainOutTime) * NextTimeScale. The clip builders make that a frame whose pose is
 * the same as this one's there, so the hand-over is seamless wherever in the window it lands. A press before the window waits for
 * it; a press after it waits for this throw to end and the next one starts from rest.
 */
USTRUCT(BlueprintType)
struct FNinjaThrowStep
{
	GENERATED_BODY()

	/** Played when this throw follows straight on from the previous one (a press queued during it). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Throw")
	TObjectPtr<UAnimSequenceBase> Animation;

	/** Played instead when the throw starts from rest (a press inside ThrowChainWindow after the last one finished). Empty = Animation. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Throw")
	TObjectPtr<UAnimSequenceBase> IdleAnimation;

	/** Where the throw starts from rest (on IdleAnimation when it is set). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Throw", meta=(ClampMin="0.0"))
	float IdleStartTime = 0.0f;

	/** Earliest point a queued press hands over to the next throw. 0 = never early: the press waits for the end. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Throw", meta=(ClampMin="0.0"))
	float ChainOutTime = 0.0f;

	/** Latest point a press still hands over; later ones wait for the end. 0 = up to the end. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Throw", meta=(ClampMin="0.0"))
	float ChainOutEndTime = 0.0f;

	/** Where the next throw's Animation starts for a hand-over exactly at ChainOutTime. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Throw", meta=(ClampMin="0.0"))
	float NextStartTime = 0.0f;

	/** Seconds into the next throw per second of this one past ChainOutTime (its frames that match this window's). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Throw", meta=(ClampMin="0.0"))
	float NextTimeScale = 0.0f;

	/** When the shuriken leaves the hand. Nothing reads it yet (no projectile); recorded for when there is one. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Throw", meta=(ClampMin="0.0"))
	float ReleaseTime = 0.0f;
};

/** One announcement of a played move, replicated to simulated proxies. Counter changing is what triggers the OnRep. */
USTRUCT()
struct FNinjaCombatMoveRep
{
	GENERATED_BODY()

	UPROPERTY()
	uint8 Counter = 0;

	UPROPERTY()
	ENinjaCombatMove Move = ENinjaCombatMove::None;

	UPROPERTY()
	uint8 Index = 0;

	/** Clip time the move started at, or negative for its default. A chained throw's entry depends on when the press landed. */
	UPROPERTY()
	float StartTime = -1.0f;
};

/**
 * Taijutsu on the Bare Ninja AnimSet (Cody bought the pack 2026-09-20 because hand-authored jabs looked bad; he picked the binds
 * himself). Plays the pack's clips on the VISIBLE mesh's full-body slot through NinjaVisual::PlaySlotMontage, the same route the
 * jutsu finishers and the air-jump flip take. Nothing here drives the capsule except the optional dodge launch: the pack's fight
 * clips have root motion switched off, and GASP owns locomotion.
 *
 * Binds (IMC_NinjaGasp, priority 1, every action bConsumeInput so GASP's IMC_Sandbox underneath never sees the key):
 *   LMB / gamepad RT  light attack, chained through LightAttacks with a cancel window
 *   E / gamepad X     heavy attack
 *   RMB / gamepad LT  block (hold; the clip pauses on the guard frame and plays out on release)
 *   Left Alt          dodge, direction from the move input
 *   1                 kunai throws, alternating through ThrowChain when pressed in succession (animation only: no projectile)
 *   F1                the aerial throw
 *   5                 shunshin (animation only for now: no teleport)
 *
 * Damage, hit detection and stamina are NOT here yet. PlayHitReaction / PlayDeath are exposed so whatever deals damage later can
 * drive the flinches, knockdowns and the get-up.
 *
 * Networking follows UNinjaAirJumpComponent: the owner plays its own move at once and tells the server, the server re-plays it and
 * bumps ReplicatedMove (COND_SkipOwner) so simulated proxies play it too. Blocking replicates as a held bool the same way.
 */
UCLASS(ClassGroup=(Ninja), meta=(BlueprintSpawnableComponent))
class DEMOGAME_1_API UNinjaCombatComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UNinjaCombatComponent();

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
	virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

	// ---------------------------------------------------------------- Input

	/** Added on possession if it isn't already in the subsystem. BP_NinjaGasp: IMC_NinjaGasp (the jutsu component adds it too). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Input")
	TObjectPtr<UInputMappingContext> InputMappingContext;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Input")
	int32 InputMappingPriority = 1;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Input")
	TObjectPtr<UInputAction> LightAttackAction;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Input")
	TObjectPtr<UInputAction> HeavyAttackAction;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Input")
	TObjectPtr<UInputAction> BlockAction;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Input")
	TObjectPtr<UInputAction> DodgeAction;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Input")
	TObjectPtr<UInputAction> KunaiAction;

	/** F1: the aerial throw, kept off 1 so the grounded throw stays quick and predictable (Cody, 2026-09-21). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Input")
	TObjectPtr<UInputAction> KunaiAerialAction;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Input")
	TObjectPtr<UInputAction> ShunshinAction;

	// ---------------------------------------------------------------- Clips

	/** The light chain, played in order and wrapping. BP_NinjaGasp: combo01_1 .. combo01_4. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Animation")
	TArray<TObjectPtr<UAnimSequenceBase>> LightAttacks;

	/** Heavies, cycled one per press. BP_NinjaGasp: attack03, attack04. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Animation")
	TArray<TObjectPtr<UAnimSequenceBase>> HeavyAttacks;

	/** Guard. Played from the start, paused at BlockHoldTime, resumed and stopped on release. Pack: defense01. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Animation")
	TObjectPtr<UAnimSequenceBase> BlockAnimation;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Animation")
	TObjectPtr<UAnimSequenceBase> DodgeBackAnimation;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Animation")
	TObjectPtr<UAnimSequenceBase> DodgeForwardAnimation;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Animation")
	TObjectPtr<UAnimSequenceBase> DodgeLeftAnimation;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Animation")
	TObjectPtr<UAnimSequenceBase> DodgeRightAnimation;

	/**
	 * The throws on 1, in order. From rest a press plays the throw the chain is up to (the first one again once ThrowChainWindow
	 * has run out); a press DURING a throw is remembered and starts the next one at the current throw's ChainOutTime, entering it
	 * at its ChainStartTime. BP_NinjaGasp: A_Throw01_WaistDraw (left-hip pouch, backhand), then A_Throw02_RisingDraw (right
	 * pocket, rising underhand). No projectile is spawned yet.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Animation")
	TArray<FNinjaThrowStep> ThrowChain;

	/** The aerial throw on F1: `attack_daggerthrow02`, a leaping near-inverted throw landing in a crouch. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Animation")
	TArray<TObjectPtr<UAnimSequenceBase>> AerialThrows;

	/** Pack: teleport_start. No teleport happens yet. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Animation")
	TObjectPtr<UAnimSequenceBase> ShunshinAnimation;

	/** Flinches, in ENinjaHitDirection order: front, back, left, right. Pack: hit_front / hit_back / hit_left / hit_right. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Animation")
	TArray<TObjectPtr<UAnimSequenceBase>> HitReactions;

	// ---------------------------------------------------------------- Tuning

	/**
	 * Earliest point in the current light attack, as a fraction of its length, at which a queued next hit may start. Before this
	 * the press is remembered, not dropped: mashing feels responsive without letting the chain skip its wind-ups.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Timing", meta=(ClampMin="0.0", ClampMax="1.0"))
	float ComboWindowStart = 0.45f;

	/** Past this fraction a press no longer chains, so a late mash restarts the chain at hit 1 instead of extending it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Timing", meta=(ClampMin="0.0", ClampMax="1.0"))
	float ComboWindowEnd = 1.0f;

	/** How long after a chain ends the next press still counts as continuing it rather than starting over. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Timing", meta=(ClampMin="0.0"))
	float ComboResetTime = 0.6f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Timing", meta=(ClampMin="0.1"))
	float AttackPlayRate = 1.0f;

	/**
	 * The throws play faster than the attacks (Cody, 2026-09-21: "Make the animation faster so we throw faster"). The pack's
	 * clips are 1.40 s and 1.43 s, which is slow for a thrown weapon; 1.5 brought them to about 0.94 s, then "super fast" took
	 * the grounded one to 3.0, about 0.47 s, and the aerial one stayed at 1.5. These defaults are the real speeds; BP_NinjaGasp
	 * may hold a slowed development value instead (setup_combat.py KUNAI_DEV_RATE). `ninja.throw.rate <n>` overrides both live.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Timing", meta=(ClampMin="0.1"))
	float KunaiPlayRate = 3.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Timing", meta=(ClampMin="0.1"))
	float AerialThrowPlayRate = 1.5f;

	/**
	 * How long after a throw FINISHES a press of 1 still does the next throw of ThrowChain rather than the first (Cody: "within a
	 * timeframe (lets say 2 seconds)"). Counted from the end, not the press, so it means the same at any play rate.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Timing", meta=(ClampMin="0.0"))
	float ThrowChainWindow = 2.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Timing", meta=(ClampMin="0.0"))
	float AttackBlendIn = 0.08f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Timing", meta=(ClampMin="0.0"))
	float AttackBlendOut = 0.2f;

	/** Clip time the guard clip pauses at. defense01 raises the guard over roughly its first third. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Timing", meta=(ClampMin="0.0"))
	float BlockHoldTime = 0.55f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Timing", meta=(ClampMin="0.0"))
	float BlockBlendIn = 0.12f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Timing", meta=(ClampMin="0.0"))
	float BlockBlendOut = 0.2f;

	/**
	 * Horizontal speed a dodge launches with. The pack's avoid / dash clips carry no root motion, so without this the ninja mimes
	 * the dodge on the spot. 0 turns the launch off.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat|Timing", meta=(ClampMin="0.0"))
	float DodgeLaunchSpeed = 600.0f;

	/** Attacks plant the ninja: GASP would otherwise keep sliding the capsule under a committed swing. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Ninja|Combat")
	bool bStopMovementOnAttack = true;

	// ---------------------------------------------------------------- Queries and hooks

	UFUNCTION(BlueprintPure, Category="Ninja|Combat")
	bool IsAttacking() const { return CurrentMove == ENinjaCombatMove::LightAttack || CurrentMove == ENinjaCombatMove::HeavyAttack; }

	UFUNCTION(BlueprintPure, Category="Ninja|Combat")
	bool IsBusy() const { return CurrentMove != ENinjaCombatMove::None; }

	UFUNCTION(BlueprintPure, Category="Ninja|Combat")
	bool IsBlocking() const { return bBlocking; }

	UFUNCTION(BlueprintPure, Category="Ninja|Combat")
	ENinjaCombatMove GetCurrentMove() const { return CurrentMove; }

	/** Plays a flinch. For whatever deals damage later; it cancels whatever the ninja was doing. */
	UFUNCTION(BlueprintCallable, Category="Ninja|Combat")
	void PlayHitReaction(ENinjaHitDirection Direction);

	/** Ends any move and lets GASP have the body back. */
	UFUNCTION(BlueprintCallable, Category="Ninja|Combat")
	void CancelMove();

private:
	ACharacter* GetCharacter() const;
	bool CanAct() const;
	float Now() const;

	void UpdateInputBinding();
	void UpdateMove(float DeltaTime);

	/** Owner-side entry: checks CanAct, plays locally, then tells the server. StartTime < 0 = the move's default start. */
	void StartMove(ENinjaCombatMove Move, uint8 Index, float StartTime = -1.0f);
	/** Plays the clip and sets the state. Runs on every machine that should see the move. */
	bool PlayMoveLocal(ENinjaCombatMove Move, uint8 Index, float StartTime = -1.0f);
	UAnimSequenceBase* GetMoveAnimation(ENinjaCombatMove Move, uint8 Index) const;

	void StartBlock();
	void StopBlock();
	void SetBlockLocal(bool bNewBlocking);

	ENinjaDodgeDirection ChooseDodgeDirection() const;
	/** Shoves the capsule the way the dodge clip mimes; the pack's avoid / dash clips carry no root motion. */
	void LaunchDodge(ENinjaDodgeDirection Direction) const;

	UFUNCTION()
	void OnLightAttackInput();
	UFUNCTION()
	void OnHeavyAttackInput();
	UFUNCTION()
	void OnBlockPressed();
	UFUNCTION()
	void OnBlockReleased();
	UFUNCTION()
	void OnDodgeInput();
	UFUNCTION()
	void OnKunaiInput();
	UFUNCTION()
	void OnKunaiAerialInput();
	/** Throws play faster than attacks, so the rate depends on which move this is. */
	float RateForMove(ENinjaCombatMove Move) const;
	UFUNCTION()
	void OnShunshinInput();

	/** A dodge carries its direction in Index (ENinjaDodgeDirection), so proxies pick the same clip without a second field. */
	UFUNCTION(Server, Reliable)
	void ServerPlayMove(ENinjaCombatMove Move, uint8 Index, float StartTime);

	UFUNCTION(Server, Reliable)
	void ServerSetBlocking(bool bNewBlocking);

	UFUNCTION()
	void OnRep_ReplicatedMove();

	UFUNCTION()
	void OnRep_BlockingReplicated();

	/** Bumped by the server for every move worth showing elsewhere; simulated proxies play it in the OnRep. */
	UPROPERTY(ReplicatedUsing=OnRep_ReplicatedMove)
	FNinjaCombatMoveRep ReplicatedMove;

	UPROPERTY(ReplicatedUsing=OnRep_BlockingReplicated)
	bool bBlockingReplicated = false;

	ENinjaCombatMove CurrentMove = ENinjaCombatMove::None;
	uint8 CurrentIndex = 0;
	float MoveElapsed = 0.0f;
	float MoveDuration = 0.0f;

	/** Set by a press during an attack; consumed once MoveElapsed passes ComboWindowStart. */
	bool bQueuedNext = false;
	/** Where the light chain is up to, and when it stops counting as the same chain. */
	uint8 ComboIndex = 0;
	float ComboExpiryTime = 0.0f;
	/** Cycles HeavyAttacks / AerialThrows so repeats don't look identical. */
	uint8 HeavyIndex = 0;
	uint8 AerialIndex = 0;

	/**
	 * A Kunai move's Index is the ThrowChain step, with this bit set when it was chained into (a queued press) rather than started
	 * from rest. The bit rides through ServerPlayMove and ReplicatedMove, so every machine picks the same clip and start frame.
	 */
	static constexpr uint8 ThrowChainedFlag = 0x80;
	/** The ThrowChain step the next press from rest plays, and when that stops counting as the same chain. */
	uint8 KunaiIndex = 0;
	float ThrowChainExpiryTime = 0.0f;
	const FNinjaThrowStep* GetThrowStep(uint8 Index) const;
	/** Clip time the move starts at: Requested when given, else 0 except for a throw from rest (its IdleStartTime). Clamped. */
	float StartTimeForMove(ENinjaCombatMove Move, uint8 Index, const UAnimSequenceBase* Clip, float Requested) const;
	/** Clip time of the move playing now. */
	float CurrentClipTime() const { return CurrentStartTime + MoveElapsed * CurrentRate; }
	/** A throw press that landed after the current throw's ChainOutEndTime: it waits for the end and starts the next from rest. */
	bool bThrowQueuedLate = false;

	/** Where in its clip the current move started, and how fast it plays, so UpdateMove can tell the current clip time. */
	float CurrentStartTime = 0.0f;
	float CurrentRate = 1.0f;

	bool bBlocking = false;
	bool bBlockPaused = false;
	float BlockElapsed = 0.0f;

	TWeakObjectPtr<UAnimMontage> CurrentMontage;
	TWeakObjectPtr<UAnimMontage> BlockMontage;
	TWeakObjectPtr<UInputComponent> BoundInputComponent;
};
