// Copyright Epic Games, Inc. All Rights Reserved.

#include "NinjaCombatComponent.h"

#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequenceBase.h"
#include "Components/SkeletalMeshComponent.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "Net/UnrealNetwork.h"
#include "NinjaJutsuComponent.h"
#include "NinjaStanceComponent.h"
#include "NinjaVisual.h"

DEFINE_LOG_CATEGORY_STATIC(LogNinjaCombat, Log, All);

/** Throw speed is judged by playing, so both throw rates can be dialled in during PIE. 0 uses the component's values. */
static TAutoConsoleVariable<float> CVarNinjaThrowRate(
	TEXT("ninja.throw.rate"), 0.0f,
	TEXT("Override the play rate of both kunai throws. 0 uses the component's KunaiPlayRate / AerialThrowPlayRate."),
	ECVF_Default);

static TAutoConsoleVariable<int32> CVarNinjaCombatDebug(
	TEXT("ninja.combat.debug"), 0, TEXT("Log every taijutsu move the combat component starts."), ECVF_Default);

UNinjaCombatComponent::UNinjaCombatComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	// After the movement component, so GetLastMovementInputVector holds the direction this frame's input asked for.
	PrimaryComponentTick.TickGroup = TG_PostPhysics;
	SetIsReplicatedByDefault(true);
}

void UNinjaCombatComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
	Super::GetLifetimeReplicatedProps(OutLifetimeProps);
	// The owner already played its own move; only the other machines need telling.
	DOREPLIFETIME_CONDITION(UNinjaCombatComponent, ReplicatedMove, COND_SkipOwner);
	DOREPLIFETIME_CONDITION(UNinjaCombatComponent, bBlockingReplicated, COND_SkipOwner);
}

ACharacter* UNinjaCombatComponent::GetCharacter() const
{
	return Cast<ACharacter>(GetOwner());
}

float UNinjaCombatComponent::Now() const
{
	const UWorld* World = GetWorld();
	return World ? World->GetTimeSeconds() : 0.0f;
}

void UNinjaCombatComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	UpdateInputBinding();
	UpdateMove(DeltaTime);
}

// ---------------------------------------------------------------- Input

void UNinjaCombatComponent::UpdateInputBinding()
{
	const APawn* Pawn = Cast<APawn>(GetOwner());
	UInputComponent* Input = Pawn ? Pawn->InputComponent.Get() : nullptr;
	APlayerController* PC = Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr;
	// A shadow clone has no controller of its own and must never take the player's keys.
	if (!Input || !PC || !PC->IsLocalController())
	{
		BoundInputComponent.Reset();
		return;
	}
	if (BoundInputComponent.Get() == Input)
	{
		return;
	}
	BoundInputComponent = Input;
	if (UEnhancedInputComponent* Enhanced = Cast<UEnhancedInputComponent>(Input))
	{
		// Our actions carry no triggers, so Started is the press and Completed the release (see IA_LockOn in CLAUDE.md).
		if (LightAttackAction)
		{
			Enhanced->BindAction(LightAttackAction, ETriggerEvent::Started, this, &UNinjaCombatComponent::OnLightAttackInput);
		}
		if (HeavyAttackAction)
		{
			Enhanced->BindAction(HeavyAttackAction, ETriggerEvent::Started, this, &UNinjaCombatComponent::OnHeavyAttackInput);
		}
		if (BlockAction)
		{
			Enhanced->BindAction(BlockAction, ETriggerEvent::Started, this, &UNinjaCombatComponent::OnBlockPressed);
			Enhanced->BindAction(BlockAction, ETriggerEvent::Completed, this, &UNinjaCombatComponent::OnBlockReleased);
			Enhanced->BindAction(BlockAction, ETriggerEvent::Canceled, this, &UNinjaCombatComponent::OnBlockReleased);
		}
		if (DodgeAction)
		{
			Enhanced->BindAction(DodgeAction, ETriggerEvent::Started, this, &UNinjaCombatComponent::OnDodgeInput);
		}
		if (KunaiAction)
		{
			Enhanced->BindAction(KunaiAction, ETriggerEvent::Started, this, &UNinjaCombatComponent::OnKunaiInput);
		}
		if (KunaiAerialAction)
		{
			Enhanced->BindAction(KunaiAerialAction, ETriggerEvent::Started, this, &UNinjaCombatComponent::OnKunaiAerialInput);
		}
		if (ShunshinAction)
		{
			Enhanced->BindAction(ShunshinAction, ETriggerEvent::Started, this, &UNinjaCombatComponent::OnShunshinInput);
		}
	}
	if (InputMappingContext)
	{
		if (UEnhancedInputLocalPlayerSubsystem* Subsystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
		{
			if (!Subsystem->HasMappingContext(InputMappingContext))
			{
				Subsystem->AddMappingContext(InputMappingContext, InputMappingPriority);
			}
		}
	}
}

void UNinjaCombatComponent::OnLightAttackInput()
{
	if (CVarNinjaCombatDebug.GetValueOnGameThread() != 0)
	{
		UE_LOG(LogNinjaCombat, Log, TEXT("%s: light press (current=%d elapsed=%.2f/%.2f queued=%d combo=%d)"),
			*GetNameSafe(GetOwner()), static_cast<int32>(CurrentMove), MoveElapsed, MoveDuration, bQueuedNext ? 1 : 0, ComboIndex);
	}
	// Mid-chain: remember the press and let UpdateMove spend it at the cancel window, so mashing never skips a wind-up.
	if (CurrentMove == ENinjaCombatMove::LightAttack && MoveDuration > 0.0f)
	{
		if (MoveElapsed <= ComboWindowEnd * MoveDuration)
		{
			bQueuedNext = true;
		}
		return;
	}
	if (LightAttacks.Num() == 0)
	{
		return;
	}
	// A press soon after the last hit continues the chain; a late one starts it over.
	if (Now() > ComboExpiryTime)
	{
		ComboIndex = 0;
	}
	StartMove(ENinjaCombatMove::LightAttack, ComboIndex);
}

void UNinjaCombatComponent::OnHeavyAttackInput()
{
	if (HeavyAttacks.Num() == 0)
	{
		return;
	}
	StartMove(ENinjaCombatMove::HeavyAttack, HeavyIndex);
}

void UNinjaCombatComponent::OnBlockPressed()
{
	StartBlock();
}

void UNinjaCombatComponent::OnBlockReleased()
{
	StopBlock();
}

void UNinjaCombatComponent::OnDodgeInput()
{
	StartMove(ENinjaCombatMove::Dodge, static_cast<uint8>(ChooseDodgeDirection()));
}

void UNinjaCombatComponent::OnKunaiInput()
{
	if (ThrowChain.Num() == 0)
	{
		return;
	}
	if (CVarNinjaCombatDebug.GetValueOnGameThread() != 0)
	{
		UE_LOG(LogNinjaCombat, Log, TEXT("%s: throw press (current=%d elapsed=%.2f/%.2f queued=%d next step=%d window left=%.2f)"),
			*GetNameSafe(GetOwner()), static_cast<int32>(CurrentMove), MoveElapsed, MoveDuration, bQueuedNext ? 1 : 0, KunaiIndex,
			ThrowChainExpiryTime - Now());
	}
	// Mid-throw: remember the press. UpdateMove spends it inside this throw's chain window, where the next throw's draw picks up
	// from this one's pose - that hand-over is what makes spamming 1 flow instead of reset between throws. A press after the window
	// has nothing to hand over to, so it waits for the end and the next throw starts from rest.
	if (CurrentMove == ENinjaCombatMove::Kunai)
	{
		const FNinjaThrowStep* Step = GetThrowStep(CurrentIndex);
		bQueuedNext = true;
		bThrowQueuedLate = Step && Step->ChainOutEndTime > 0.0f && CurrentClipTime() > Step->ChainOutEndTime;
		return;
	}
	// From rest: soon after the last throw carries on the chain, a late press starts it over.
	if (Now() > ThrowChainExpiryTime)
	{
		KunaiIndex = 0;
	}
	StartMove(ENinjaCombatMove::Kunai, KunaiIndex);
}

void UNinjaCombatComponent::OnKunaiAerialInput()
{
	if (AerialThrows.Num() == 0)
	{
		return;
	}
	StartMove(ENinjaCombatMove::KunaiAerial, AerialIndex);
}

void UNinjaCombatComponent::OnShunshinInput()
{
	StartMove(ENinjaCombatMove::Shunshin, 0);
}

// ---------------------------------------------------------------- Moves

bool UNinjaCombatComponent::CanAct() const
{
	const ACharacter* Character = GetCharacter();
	const UCharacterMovementComponent* Movement = Character ? Character->GetCharacterMovement() : nullptr;
	if (!Movement || !Movement->IsMovingOnGround())
	{
		return false;
	}
	// Same gates the seals use: not lying down, not mid-cast, not inside one of GASP's traversal montages.
	if (const UNinjaStanceComponent* Stance = Character->FindComponentByClass<UNinjaStanceComponent>(); Stance && Stance->IsProne())
	{
		return false;
	}
	if (const UNinjaJutsuComponent* Jutsu = Character->FindComponentByClass<UNinjaJutsuComponent>();
		Jutsu && (Jutsu->IsCastingJutsu() || Jutsu->IsFinishing()))
	{
		return false;
	}
	const UAnimInstance* BodyAnim = Character->GetMesh() ? Character->GetMesh()->GetAnimInstance() : nullptr;
	return !BodyAnim || !BodyAnim->IsSlotActive(NinjaVisual::FullBodySlot);
}

UAnimSequenceBase* UNinjaCombatComponent::GetMoveAnimation(ENinjaCombatMove Move, uint8 Index) const
{
	auto Pick = [](const TArray<TObjectPtr<UAnimSequenceBase>>& Clips, uint8 At) -> UAnimSequenceBase*
	{
		return Clips.Num() > 0 ? Clips[At % Clips.Num()].Get() : nullptr;
	};

	switch (Move)
	{
	case ENinjaCombatMove::LightAttack:
		return Pick(LightAttacks, Index);
	case ENinjaCombatMove::HeavyAttack:
		return Pick(HeavyAttacks, Index);
	case ENinjaCombatMove::Kunai:
		if (const FNinjaThrowStep* Step = GetThrowStep(Index))
		{
			const bool bChained = (Index & ThrowChainedFlag) != 0;
			return (!bChained && Step->IdleAnimation) ? Step->IdleAnimation.Get() : Step->Animation.Get();
		}
		return nullptr;
	case ENinjaCombatMove::KunaiAerial:
		return Pick(AerialThrows, Index);
	case ENinjaCombatMove::HitReaction:
		return Pick(HitReactions, Index);
	case ENinjaCombatMove::Shunshin:
		return ShunshinAnimation;
	case ENinjaCombatMove::Dodge:
		switch (static_cast<ENinjaDodgeDirection>(Index))
		{
		case ENinjaDodgeDirection::Forward:
			return DodgeForwardAnimation;
		case ENinjaDodgeDirection::Left:
			return DodgeLeftAnimation;
		case ENinjaDodgeDirection::Right:
			return DodgeRightAnimation;
		default:
			return DodgeBackAnimation;
		}
	default:
		return nullptr;
	}
}

const FNinjaThrowStep* UNinjaCombatComponent::GetThrowStep(uint8 Index) const
{
	const int32 Num = ThrowChain.Num();
	return Num > 0 ? &ThrowChain[(Index & ~ThrowChainedFlag) % Num] : nullptr;
}

float UNinjaCombatComponent::StartTimeForMove(ENinjaCombatMove Move, uint8 Index, const UAnimSequenceBase* Clip, float Requested) const
{
	if (!Clip)
	{
		return 0.0f;
	}
	float Start = Requested;
	if (Start < 0.0f)
	{
		// A chained throw always arrives with the entry its hand-over computed, so only a throw from rest has a default here.
		const FNinjaThrowStep* Step = Move == ENinjaCombatMove::Kunai ? GetThrowStep(Index) : nullptr;
		Start = (Step && (Index & ThrowChainedFlag) == 0) ? Step->IdleStartTime : 0.0f;
	}
	// A start past the end would play nothing and leave the move "busy" for a negative duration.
	return FMath::Clamp(Start, 0.0f, FMath::Max(Clip->GetPlayLength() - 0.05f, 0.0f));
}

void UNinjaCombatComponent::StartMove(ENinjaCombatMove Move, uint8 Index, float StartTime)
{
	// A hit reaction is the one move allowed to interrupt; everything else waits its turn.
	if (Move != ENinjaCombatMove::HitReaction && (IsBusy() || !CanAct()))
	{
		if (CVarNinjaCombatDebug.GetValueOnGameThread() != 0)
		{
			UE_LOG(LogNinjaCombat, Log, TEXT("%s: refused move %d index %d (busy=%d current=%d canAct=%d)"),
				*GetNameSafe(GetOwner()), static_cast<int32>(Move), Index, IsBusy() ? 1 : 0,
				static_cast<int32>(CurrentMove), CanAct() ? 1 : 0);
		}
		return;
	}
	if (!PlayMoveLocal(Move, Index, StartTime))
	{
		return;
	}
	if (Move == ENinjaCombatMove::Dodge)
	{
		LaunchDodge(static_cast<ENinjaDodgeDirection>(Index));
	}
	ACharacter* Character = GetCharacter();
	if (Character && Character->HasAuthority())
	{
		ReplicatedMove.Counter++;
		ReplicatedMove.Move = Move;
		ReplicatedMove.Index = Index;
		ReplicatedMove.StartTime = StartTime;
	}
	else
	{
		ServerPlayMove(Move, Index, StartTime);
	}
}

float UNinjaCombatComponent::RateForMove(ENinjaCombatMove Move) const
{
	// `ninja.throw.rate` overrides both throws live, so the speed can be judged by playing rather than by rebuilding.
	const float Override = CVarNinjaThrowRate.GetValueOnGameThread();
	switch (Move)
	{
	case ENinjaCombatMove::Kunai:
		return FMath::IsNearlyZero(Override) ? KunaiPlayRate : Override;
	case ENinjaCombatMove::KunaiAerial:
		return FMath::IsNearlyZero(Override) ? AerialThrowPlayRate : Override;
	default:
		return AttackPlayRate;
	}
}

bool UNinjaCombatComponent::PlayMoveLocal(ENinjaCombatMove Move, uint8 Index, float StartTime)
{
	UAnimSequenceBase* Clip = GetMoveAnimation(Move, Index);
	USkeletalMeshComponent* Visual = NinjaVisual::FindVisualMesh(GetOwner());
	if (!Clip || !Visual || !Visual->GetAnimInstance())
	{
		UE_LOG(LogNinjaCombat, Warning, TEXT("%s: no clip or no visible mesh for move %d index %d"),
			*GetNameSafe(GetOwner()), static_cast<int32>(Move), Index);
		return false;
	}
	// Blocking and a move can't share the full-body slot; a move wins and the guard is dropped.
	if (bBlocking)
	{
		SetBlockLocal(false);
	}
	const float Rate = FMath::Max(RateForMove(Move), 0.1f);
	const float Start = StartTimeForMove(Move, Index, Clip, StartTime);
	// A montage's auto blend-out starts AttackBlendOut of REAL time before its end, which at a fast throw rate is well inside the
	// chain window (at 3.0 the rising throw would be ~70% faded when it hands over, and faded through its own release). Hold a
	// throw at full weight until its last hand-over point instead, then fade over the usual AttackBlendOut.
	float BlendOutTrigger = -1.0f;
	if (const FNinjaThrowStep* Step = Move == ENinjaCombatMove::Kunai ? GetThrowStep(Index) : nullptr; Step && Step->ChainOutTime > 0.0f)
	{
		const float LastHandOver = Step->ChainOutEndTime > 0.0f ? Step->ChainOutEndTime : Clip->GetPlayLength();
		BlendOutTrigger = FMath::Min(AttackBlendOut, FMath::Max(Clip->GetPlayLength() - LastHandOver, 0.0f) / Rate);
	}
	UAnimMontage* Montage = NinjaVisual::PlaySlotMontage(Visual, Clip, NinjaVisual::FullBodySlot,
		AttackBlendIn, AttackBlendOut, Rate, Start, false, true, BlendOutTrigger);
	if (!Montage)
	{
		return false;
	}
	CurrentMontage = Montage;
	CurrentMove = Move;
	CurrentIndex = Index;
	MoveElapsed = 0.0f;
	MoveDuration = (Clip->GetPlayLength() - Start) / Rate;
	CurrentStartTime = Start;
	CurrentRate = Rate;
	bQueuedNext = false;
	bThrowQueuedLate = false;

	if (bStopMovementOnAttack && (Move == ENinjaCombatMove::LightAttack || Move == ENinjaCombatMove::HeavyAttack))
	{
		if (ACharacter* Character = GetCharacter(); Character && Character->GetCharacterMovement())
		{
			Character->GetCharacterMovement()->StopMovementImmediately();
		}
	}
	if (CVarNinjaCombatDebug.GetValueOnGameThread() != 0)
	{
		UE_LOG(LogNinjaCombat, Log, TEXT("%s: move %d index %d%s, %s from %.3f s, %.2f s"), *GetNameSafe(GetOwner()),
			static_cast<int32>(Move), Index & ~ThrowChainedFlag,
			Move == ENinjaCombatMove::Kunai ? ((Index & ThrowChainedFlag) != 0 ? TEXT(" chained") : TEXT(" from rest")) : TEXT(""),
			*GetNameSafe(Clip), Start, MoveDuration);
	}
	return true;
}

void UNinjaCombatComponent::UpdateMove(float DeltaTime)
{
	// The guard clip runs to BlockHoldTime and stops there, so the ninja holds the raised guard instead of lowering it again.
	if (bBlocking && !bBlockPaused && BlockMontage.IsValid())
	{
		BlockElapsed += DeltaTime;
		if (BlockElapsed >= BlockHoldTime)
		{
			USkeletalMeshComponent* Visual = NinjaVisual::FindVisualMesh(GetOwner());
			if (UAnimInstance* Anim = Visual ? Visual->GetAnimInstance() : nullptr)
			{
				Anim->Montage_SetPlayRate(BlockMontage.Get(), 0.0f);
				bBlockPaused = true;
			}
		}
	}

	if (CurrentMove == ENinjaCombatMove::None)
	{
		return;
	}
	MoveElapsed += DeltaTime;

	// A queued light attack starts as soon as the cancel window opens: that overlap is what makes a chain read as a combo.
	if (bQueuedNext && CurrentMove == ENinjaCombatMove::LightAttack && MoveDuration > 0.0f
		&& MoveElapsed >= ComboWindowStart * MoveDuration && LightAttacks.Num() > 0)
	{
		bQueuedNext = false;
		const uint8 NextIndex = static_cast<uint8>((CurrentIndex + 1) % LightAttacks.Num());
		CurrentMove = ENinjaCombatMove::None;   // so StartMove's IsBusy gate lets the chain through
		ComboIndex = NextIndex;
		StartMove(ENinjaCombatMove::LightAttack, NextIndex);
		return;
	}

	// A queued throw hands over once this one reaches its chain window, entering the next throw at the frame whose pose matches
	// where this one has got to. A press queued before the window is spent on its first tick (clamped to the window, so a long
	// frame can't overshoot the matching range); one that arrived after it waits for the end (bThrowQueuedLate).
	if (bQueuedNext && !bThrowQueuedLate && CurrentMove == ENinjaCombatMove::Kunai && ThrowChain.Num() > 0)
	{
		const FNinjaThrowStep* Step = GetThrowStep(CurrentIndex);
		const float ClipTime = CurrentClipTime();
		if (Step && Step->ChainOutTime > 0.0f && ClipTime >= Step->ChainOutTime)
		{
			bQueuedNext = false;
			// Checked first: StartMove refusing after CurrentMove is cleared would leave this throw's montage playing untracked.
			if (CanAct())
			{
				const float WindowEnd = Step->ChainOutEndTime > 0.0f ? Step->ChainOutEndTime : ClipTime;
				const float Entry = Step->NextStartTime + (FMath::Min(ClipTime, WindowEnd) - Step->ChainOutTime) * Step->NextTimeScale;
				const uint8 Next = static_cast<uint8>(((CurrentIndex & ~ThrowChainedFlag) + 1) % ThrowChain.Num());
				KunaiIndex = Next;
				CurrentMove = ENinjaCombatMove::None;   // so StartMove's IsBusy gate lets the chain through
				StartMove(ENinjaCombatMove::Kunai, static_cast<uint8>(Next | ThrowChainedFlag), Entry);
				return;
			}
		}
	}

	if (MoveElapsed < MoveDuration)
	{
		return;
	}
	// A throw press still waiting at the end (no ChainOutTime on this step) starts the next throw from rest below.
	const bool bThrowQueued = bQueuedNext && CurrentMove == ENinjaCombatMove::Kunai;
	// Finished. Remember where the chain got to so the next press continues it for ComboResetTime.
	if (CurrentMove == ENinjaCombatMove::LightAttack && LightAttacks.Num() > 0)
	{
		ComboIndex = static_cast<uint8>((CurrentIndex + 1) % LightAttacks.Num());
		ComboExpiryTime = Now() + ComboResetTime;
	}
	else if (CurrentMove == ENinjaCombatMove::HeavyAttack && HeavyAttacks.Num() > 0)
	{
		HeavyIndex = static_cast<uint8>((CurrentIndex + 1) % HeavyAttacks.Num());
	}
	else if (CurrentMove == ENinjaCombatMove::Kunai && ThrowChain.Num() > 0)
	{
		KunaiIndex = static_cast<uint8>(((CurrentIndex & ~ThrowChainedFlag) + 1) % ThrowChain.Num());
		ThrowChainExpiryTime = Now() + ThrowChainWindow;
	}
	else if (CurrentMove == ENinjaCombatMove::KunaiAerial && AerialThrows.Num() > 0)
	{
		AerialIndex = static_cast<uint8>((CurrentIndex + 1) % AerialThrows.Num());
	}
	CurrentMove = ENinjaCombatMove::None;
	CurrentMontage.Reset();
	MoveElapsed = 0.0f;
	MoveDuration = 0.0f;
	bQueuedNext = false;
	bThrowQueuedLate = false;
	if (bThrowQueued)
	{
		StartMove(ENinjaCombatMove::Kunai, KunaiIndex);
	}
}

void UNinjaCombatComponent::CancelMove()
{
	if (CurrentMove == ENinjaCombatMove::None)
	{
		return;
	}
	if (USkeletalMeshComponent* Visual = NinjaVisual::FindVisualMesh(GetOwner()))
	{
		NinjaVisual::StopSlotMontages(Visual, NinjaVisual::FullBodySlot, AttackBlendOut);
	}
	CurrentMove = ENinjaCombatMove::None;
	CurrentMontage.Reset();
	MoveElapsed = 0.0f;
	MoveDuration = 0.0f;
	bQueuedNext = false;
	bThrowQueuedLate = false;
}

void UNinjaCombatComponent::PlayHitReaction(ENinjaHitDirection Direction)
{
	StartMove(ENinjaCombatMove::HitReaction, static_cast<uint8>(Direction));
}

// ---------------------------------------------------------------- Block

void UNinjaCombatComponent::StartBlock()
{
	if (bBlocking || IsBusy() || !BlockAnimation || !CanAct())
	{
		return;
	}
	SetBlockLocal(true);
	ACharacter* Character = GetCharacter();
	if (Character && Character->HasAuthority())
	{
		bBlockingReplicated = true;
	}
	else
	{
		ServerSetBlocking(true);
	}
}

void UNinjaCombatComponent::StopBlock()
{
	if (!bBlocking)
	{
		return;
	}
	SetBlockLocal(false);
	ACharacter* Character = GetCharacter();
	if (Character && Character->HasAuthority())
	{
		bBlockingReplicated = false;
	}
	else
	{
		ServerSetBlocking(false);
	}
}

void UNinjaCombatComponent::SetBlockLocal(bool bNewBlocking)
{
	USkeletalMeshComponent* Visual = NinjaVisual::FindVisualMesh(GetOwner());
	if (!Visual || !Visual->GetAnimInstance())
	{
		return;
	}
	if (bNewBlocking)
	{
		// bAutoBlendOut false so a guard that runs past BlockHoldTime still holds instead of dropping on its own.
		UAnimMontage* Montage = NinjaVisual::PlaySlotMontage(Visual, BlockAnimation, NinjaVisual::FullBodySlot,
			BlockBlendIn, BlockBlendOut, 1.0f, 0.0f, false, false);
		if (!Montage)
		{
			return;
		}
		BlockMontage = Montage;
		bBlocking = true;
		bBlockPaused = false;
		BlockElapsed = 0.0f;
		return;
	}
	NinjaVisual::StopSlotMontages(Visual, NinjaVisual::FullBodySlot, BlockBlendOut);
	BlockMontage.Reset();
	bBlocking = false;
	bBlockPaused = false;
	BlockElapsed = 0.0f;
}

// ---------------------------------------------------------------- Dodge

ENinjaDodgeDirection UNinjaCombatComponent::ChooseDodgeDirection() const
{
	const ACharacter* Character = GetCharacter();
	if (!Character)
	{
		return ENinjaDodgeDirection::Back;
	}
	FVector Input = Character->GetLastMovementInputVector();
	Input.Z = 0.0f;
	// No stick, no key: give ground, which is what a dodge with no direction should mean.
	if (Input.SizeSquared() < KINDA_SMALL_NUMBER)
	{
		return ENinjaDodgeDirection::Back;
	}
	Input.Normalize();
	const float Forward = FVector::DotProduct(Input, Character->GetActorForwardVector());
	const float Right = FVector::DotProduct(Input, Character->GetActorRightVector());
	if (FMath::Abs(Forward) >= FMath::Abs(Right))
	{
		return Forward >= 0.0f ? ENinjaDodgeDirection::Forward : ENinjaDodgeDirection::Back;
	}
	return Right >= 0.0f ? ENinjaDodgeDirection::Right : ENinjaDodgeDirection::Left;
}

void UNinjaCombatComponent::LaunchDodge(ENinjaDodgeDirection Direction) const
{
	ACharacter* Character = GetCharacter();
	if (!Character || DodgeLaunchSpeed <= 0.0f)
	{
		return;
	}
	// Only the machines that simulate this pawn's movement: a simulated proxy is told where it ended up anyway.
	if (!Character->HasAuthority() && !Character->IsLocallyControlled())
	{
		return;
	}
	FVector Dir;
	switch (Direction)
	{
	case ENinjaDodgeDirection::Forward:
		Dir = Character->GetActorForwardVector();
		break;
	case ENinjaDodgeDirection::Left:
		Dir = -Character->GetActorRightVector();
		break;
	case ENinjaDodgeDirection::Right:
		Dir = Character->GetActorRightVector();
		break;
	default:
		Dir = -Character->GetActorForwardVector();
		break;
	}
	Dir.Z = 0.0f;
	Dir.Normalize();
	// XY override only: a dodge shouldn't lift the ninja off the floor or cancel a fall.
	Character->LaunchCharacter(Dir * DodgeLaunchSpeed, true, false);
}

// ---------------------------------------------------------------- Network

void UNinjaCombatComponent::ServerPlayMove_Implementation(ENinjaCombatMove Move, uint8 Index, float StartTime)
{
	// The owner already decided; the server re-plays it so its own copy matches, then announces it to everyone else.
	if (!PlayMoveLocal(Move, Index, StartTime))
	{
		return;
	}
	if (Move == ENinjaCombatMove::Dodge)
	{
		LaunchDodge(static_cast<ENinjaDodgeDirection>(Index));
	}
	ReplicatedMove.Counter++;
	ReplicatedMove.Move = Move;
	ReplicatedMove.Index = Index;
	ReplicatedMove.StartTime = StartTime;
}

void UNinjaCombatComponent::ServerSetBlocking_Implementation(bool bNewBlocking)
{
	SetBlockLocal(bNewBlocking);
	bBlockingReplicated = bNewBlocking;
}

void UNinjaCombatComponent::OnRep_ReplicatedMove()
{
	PlayMoveLocal(ReplicatedMove.Move, ReplicatedMove.Index, ReplicatedMove.StartTime);
}

void UNinjaCombatComponent::OnRep_BlockingReplicated()
{
	SetBlockLocal(bBlockingReplicated);
}
